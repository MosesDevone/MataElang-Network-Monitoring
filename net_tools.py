"""
Utilities for advanced network tools (Traceroute & Speedtest) & Reporting
"""
import asyncio
import io
from datetime import datetime
from icmplib import traceroute
import speedtest
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy.orm import Session
import crud
import schemas
import csv


# --- Traceroute ---
async def perform_traceroute(target: str):
    """
    Perform traceroute to target (Blocking run in thread)
    Returns list of hops
    """
    loop = asyncio.get_event_loop()
    try:
        # Clean target if it's a URL
        from urllib.parse import urlparse
        hostname = target
        if "://" in target:
            try:
                parsed = urlparse(target)
                hostname = parsed.hostname or target
            except:
                pass

        # Run sync traceroute in thread pool
        hops = await loop.run_in_executor(None, lambda: traceroute(hostname, count=1, interval=0.05, timeout=1, max_hops=15))
        
        results = []
        for hop in hops:
            results.append({
                "distance": hop.distance,
                "address": hop.address,
                "avg_rtt": hop.avg_rtt,
                "packet_loss": hop.packet_loss,
                "is_alive": hop.is_alive
            })
        return results
    except Exception as e:
        return {"error": str(e)}

async def perform_geotraceroute(target: str):
    """
    Perform traceroute and resolve GeoIP for each hop
    """
    hops = await perform_traceroute(target)
    if isinstance(hops, dict) and "error" in hops:
        return hops

    geohops = []
    for hop in hops:
        if hop["address"] and hop["address"] != "0.0.0.0":
            # Avoid resolving local/private IPs if possible, but ip-api handles them gracefully
            geo = await resolve_geoip(hop["address"])
            if geo:
                hop.update(geo)
        geohops.append(hop)
    return geohops

# --- GeoIP ---
async def resolve_geoip(target: str):
    """
    Resolve IP to Location (Lat, Lon, Country, City)
    Using ip-api.com (Free, no key required for low usage)
    """
    import aiohttp
    import socket
    from urllib.parse import urlparse
    
    # Clean target if it's a URL
    hostname = target
    if "://" in target:
        try:
            parsed = urlparse(target)
            hostname = parsed.hostname or target
        except:
            pass
    
    # Resolve domain to IP first
    try:
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        # If passed an IP or invalid hostname
        ip_address = hostname
        
    url = f"http://ip-api.com/json/{ip_address}?fields=status,country,city,lat,lon,query"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return {
                            "latitude": data.get("lat"),
                            "longitude": data.get("lon"),
                            "country": data.get("country"),
                            "city": data.get("city"),
                            "ip": data.get("query")
                        }
        except Exception as e:
            print(f"GeoIP Error: {e}")
            
    return None

# --- Speedtest ---
def perform_speedtest():
    """
    Run speedtest-cli. This is blocking, run in executor!
    """
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Convert to Mbps
        upload = st.upload() / 1_000_000      # Convert to Mbps
        ping = st.results.ping
        
        return {
            "download": round(download, 2),
            "upload": round(upload, 2),
            "ping": round(ping, 2),
            "client": st.results.client,
            "share": st.results.share()
        }
    except Exception as e:
        return {"error": str(e)}

# --- PDF Report ---
def generate_sla_report(db: Session, monitor_id: int):
    """
    Generate PDF SLA Report
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Fetch Data
    stats = crud.get_uptime_stats(db, monitor_id, hours=720) # 30 Days stats
    monitor = crud.get_monitor(db, monitor_id)
    incidents = crud.get_incidents(db, monitor_id, hours=720)

    # Title
    elements.append(Paragraph(f"SLA Report: {monitor.name}", styles['Title']))
    elements.append(Paragraph(f"Target: {monitor.target} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Summary Table
    data = [
        ["Metric", "Value"],
        ["30-Day Uptime", f"{stats.uptime_percentage:.2f}%"],
        ["Total Downtime Incidents", len(incidents)],
        ["Average Latency", f"{stats.average_latency:.2f} ms" if stats.average_latency else "-"],
        ["Average Packet Loss", f"{stats.average_packet_loss:.2f} %"]
    ]
    t = Table(data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Incident Log
    if incidents:
        elements.append(Paragraph("Major Incidents (Last 30 Days)", styles['Heading2']))
        incident_data = [["Start Time", "Duration", "Status"]]
        for inc in incidents[:20]: # Limit to top 20
            duration = f"{inc.duration_seconds}s" if inc.duration_seconds else "Ongoing"
            incident_data.append([
                inc.start_time.strftime('%Y-%m-%d %H:%M'),
                duration,
                "RESOLVED" if not inc.is_ongoing else "ONGOING"
            ])
        
        t2 = Table(incident_data, colWidths=[150, 100, 100])
        t2.setStyle(TableStyle([
             ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
             ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
             ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t2)
    else:
        elements.append(Paragraph("No downtime recorded in the last 30 days. Excellent stability!", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_sla_csv(db: Session, monitor_id: int):
    """
    Generate CSV SLA Report
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Fetch Data
    stats = crud.get_uptime_stats(db, monitor_id, hours=720)
    monitor = crud.get_monitor(db, monitor_id)
    incidents = crud.get_incidents(db, monitor_id, hours=720)
    
    # Header
    writer.writerow(["MatEl SLA Report", monitor.name, monitor.target])
    writer.writerow(["Generated At", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([])
    
    # Summary
    writer.writerow(["Summary Statistics (Last 30 Days)"])
    writer.writerow(["Uptime Percentage", f"{stats.uptime_percentage:.2f}%"])
    writer.writerow(["Total Incidents", len(incidents)])
    writer.writerow(["Avg Latency (ms)", round(stats.average_latency, 2) if stats.average_latency else "-"])
    writer.writerow([])
    
    # Incidents
    writer.writerow(["Incident Log"])
    writer.writerow(["Start Time", "Duration (s)", "Status"])
    for inc in incidents:
        writer.writerow([
            inc.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            inc.duration_seconds if inc.duration_seconds else "Ongoing",
            "RESOLVED" if not inc.is_ongoing else "ONGOING"
        ])
    
    return output.getvalue()
