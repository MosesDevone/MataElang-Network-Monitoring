"""
Asynchronous monitoring engine for HTTP and ICMP checks
"""
import asyncio
import aiohttp
import time
from typing import Tuple, Optional
from icmplib import async_ping
from models import MonitorType, MonitorStatus
from schemas import HeartbeatCreate
import logging
import re
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringEngine:
    """
    Asynchronous monitoring engine yang melakukan checks secara concurrent
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start(self):
        """Initialize aiohttp session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def stop(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def check_http(self, target: str, expected_hash: Optional[str] = None) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Check HTTP endpoint and content integrity
        Returns: (status, latency_ms, packet_loss_percent, error_message)
        """
        import hashlib
        try:
            if not self.session:
                await self.start()
            
            # Ensure URL has protocol
            if not target.startswith(('http://', 'https://')):
                target = f'http://{target}'
            
            start_time = time.time()
            async with self.session.get(target) as response:
                content = await response.read()
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status >= 200 and response.status < 400:
                    # Defacement Check
                    if expected_hash:
                        current_hash = hashlib.sha256(content).hexdigest()
                        if current_hash != expected_hash:
                            return MonitorStatus.DOWN, latency, 0.0, "Integrity Check Failed: Content Changed!"
                    
                    return MonitorStatus.UP, latency, 0.0, None
                else:
                    return MonitorStatus.DOWN, latency, 100.0, f"HTTP {response.status}"
        
        except asyncio.TimeoutError:
            return MonitorStatus.DOWN, None, 100.0, "Timeout"
        except aiohttp.ClientError as e:
            return MonitorStatus.DOWN, None, 100.0, f"Connection error: {str(e)}"
        except Exception as e:
            logger.error(f"HTTP check error for {target}: {e}")
            return MonitorStatus.DOWN, None, 100.0, str(e)
    
    async def check_icmp(self, target: str) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Check ICMP ping
        Returns: (status, latency_ms, packet_loss_percent, error_message)
        """
        try:
            # Remove protocol if present
            target = target.replace('http://', '').replace('https://', '').split('/')[0]
            
            # Perform async ping
            host = await async_ping(target, count=4, timeout=2, privileged=False)
            
            latency = host.avg_rtt
            packet_loss = host.packet_loss
            
            if host.is_alive:
                return MonitorStatus.UP, latency, packet_loss, None
            else:
                return MonitorStatus.DOWN, None, packet_loss, "Host unreachable"
        
        except Exception as e:
            logger.error(f"ICMP check error for {target}: {e}")
            return MonitorStatus.DOWN, None, 100.0, str(e)

    async def check_port_scan(self, target: str, expected_ports: Optional[str] = None) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Scan common ports and compare with baseline
        Returns: (status, open_ports_count, 0.0, info_message)
        """
        import socket
        import asyncio
        
        # Clean target
        hostname = target.replace('http://', '').replace('https://', '').split('/')[0]
        
        # Ports to scan (Common critical ports)
        ports_to_scan = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 1433, 3306, 3389, 5432, 8080, 8443]
        
        # If user has specific expected ports, add them if not in list
        if expected_ports:
            try:
                e_ports = [int(p.strip()) for p in expected_ports.split(',') if p.strip()]
                for p in e_ports:
                    if p not in ports_to_scan:
                        ports_to_scan.append(p)
            except:
                pass

        async def is_port_open(port):
            try:
                # Use asyncio.open_connection for async port checking
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(hostname, port),
                    timeout=2.0
                )
                writer.close()
                await writer.wait_closed()
                return port
            except:
                return None

        start_time = time.time()
        # Scan ports concurrently
        tasks = [is_port_open(p) for p in ports_to_scan]
        results = await asyncio.gather(*tasks)
        
        open_ports = [p for p in results if p is not None]
        latency = (time.time() - start_time) * 1000
        
        open_ports_str = ",".join(map(str, sorted(open_ports)))
        
        if expected_ports:
            # Baseline check: Are there any ports open that are NOT in the baseline?
            expected_list = [p.strip() for p in expected_ports.split(',') if p.strip()]
            unexpected_ports = [str(p) for p in open_ports if str(p) not in expected_list]
            
            if unexpected_ports:
                return MonitorStatus.DOWN, latency, 0.0, f"SECURITY ALERT: Unexpected open ports found: {','.join(unexpected_ports)}!"
            
            return MonitorStatus.UP, latency, 0.0, f"Protected: {len(open_ports)} ports open (Matching baseline)"
        
        return MonitorStatus.UP, latency, 0.0, f"Open ports found: {open_ports_str or 'None'}"

    async def check_ssl(self, target: str) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Check SSL certificate expiry
        Returns: (status, days_remaining, 0.0, info_message)
        """
        import socket
        import ssl
        from datetime import datetime

        try:
            # Clean target
            hostname = target.replace('http://', '').replace('https://', '').split('/')[0]
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse expiry date
                    expire_date_str = cert.get('notAfter')
                    expire_date = datetime.strptime(expire_date_str, '%b %d %H:%M:%S %Y %Z')
                    
                    remaining = (expire_date - datetime.utcnow()).days
                    
                    if remaining <= 0:
                        return MonitorStatus.DOWN, 0.0, 100.0, f"SSL Expired! ({expire_date_str})"
                    elif remaining < 7:
                        return MonitorStatus.DOWN, float(remaining), 0.0, f"CRITICAL: SSL expires in {remaining} days!"
                    elif remaining < 30:
                        return MonitorStatus.UP, float(remaining), 0.0, f"WARNING: SSL expires in {remaining} days"
                    else:
                        return MonitorStatus.UP, float(remaining), 0.0, f"SSL Valid till {expire_date.strftime('%Y-%m-%d')}"
                        
        except Exception as e:
            logger.error(f"SSL check error for {target}: {e}")
            return MonitorStatus.DOWN, None, 100.0, f"SSL Error: {str(e)}"

    async def check_ghost_paths(self, target: str) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Deep Scan for sensitive file exposure (Upgraded Ghost Path Scanner)
        """
        if not self.session:
            await self.start()
            
        base_url = target.rstrip('/')
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url

    async def check_ghost_paths(self, target: str) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        High-Intensity Security Crawler (Ghost Path Explorer 5.0)
        """
        if not self.session:
            await self.start()
            
        parsed_target = urlparse(target if target.startswith('http') else 'https://' + target)
        base_url = f"{parsed_target.scheme}://{parsed_target.netloc}"
        start_path = parsed_target.path if parsed_target.path else "/"

        found_vulnerabilities = []
        visited_urls = set()
        # Start from the root AND the specific path provided by the user
        to_crawl = [(base_url + start_path, 0), (base_url + "/", 0)]
        max_pages = 40 # Increased intensity
        max_depth = 5
        start_time = time.time()

        # 1. PASSIVE DISCOVERY: robots.txt
        try:
            async with self.session.get(base_url + "/robots.txt", timeout=5) as rb:
                if rb.status == 200:
                    rb_text = await rb.text()
                    disallowed = re.findall(r'Disallow:\s*(/[^\s#]+)', rb_text)
                    for d in disallowed:
                        to_crawl.append((urljoin(base_url, d.split('*')[0]), 1))
        except: pass

        # 2. ACTIVE FUZZING (More aggressive seeds)
        fuzz_seeds = [
            '/api/', '/v1/', '/v2/', '/dev/', '/test/', '/backup/', '/old/', '/storage/',
            '/REDCap/', '/redcap/', '/Resources/', '/js/', '/vue/', '/assets/',
            '/admin/', '/config/', '/uploads/', '/tmp/', '/private/', '/.git/'
        ]
        for s in fuzz_seeds:
            to_crawl.append((urljoin(base_url, s), 1))

        async def audit_url(url, depth):
            if url in visited_urls or len(visited_urls) >= max_pages: return
            visited_urls.add(url)
            
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MatEl-Security-Spider/5.0'}
                async with self.session.get(url, timeout=7, allow_redirects=True, headers=headers) as response:
                    content = await response.read()
                    content_str = content.decode('utf-8', errors='ignore').lower()
                    
                    # DIRECTORY LISTING DETECTION (Stronger patterns)
                    dl_patterns = ['index of', 'parent directory', 'last modified', 'directory listing', 'folder listing']
                    if response.status == 200 and any(p in content_str for p in dl_patterns):
                        # Verify it's a real listing page (usually contains links and simple layout)
                        if '<table' in content_str or '<pre' in content_str or 'href=' in content_str:
                            path_display = urlparse(url).path or '/'
                            found_vulnerabilities.append(f"{path_display} [DIRECTORY LISTING]")

                    # SCRAPE LINKS (Recursive depth)
                    if depth < max_depth:
                        # Find both HTML links and JS-like paths
                        links = re.findall(r'(?:href|src)=["\'](.[^"\']+)["\']', content_str)
                        # Also look for paths in strings (basic JS scraping)
                        js_paths = re.findall(r'["\'](/[a-zA-Z0-9\-_/]+\.[a-z0-9]+|[a-zA-Z0-9\-_/]+/)["\']', content_str)
                        
                        all_discovered = set(links + js_paths)
                        for link in all_discovered:
                            full_link = urljoin(url, link)
                            p_link = urlparse(full_link)
                            
                            # Stay on same domain and within reasonable length
                            if p_link.netloc == parsed_target.netloc and len(p_link.path) < 150:
                                # Prioritize directories or sensitive files
                                if p_link.path.endswith('/') or any(ext in p_link.path for ext in ['.env', '.js', '.json', '.sql', '.php']):
                                    if full_link not in visited_urls:
                                        to_crawl.append((full_link, depth + 1))
            except: pass

        # Execution Loop (Crawling)
        current_idx = 0
        while current_idx < len(to_crawl) and len(visited_urls) < max_pages:
            url, depth = to_crawl[current_idx]
            await audit_url(url, depth)
            current_idx += 1

        # PROBING PHASE (Check sensitive files in every discovered directory)
        probe_list = ['.env', '.git/config', '.vscode/settings.json', 'web.config', 'phpinfo.php', 'config.php.bak']
        dirs_to_probe = {u if u.endswith('/') else u.rsplit('/', 1)[0] + '/' for u in visited_urls}
        
        tasks = []
        for d in dirs_to_probe:
            for f in probe_list:
                tasks.append(self._probe_sensitive_file(d + f))
        
        results = await asyncio.gather(*tasks)
        found_vulnerabilities.extend([p for p in results if p is not None])

        latency = (time.time() - start_time) * 1000
        if found_vulnerabilities:
            unique = list(set(found_vulnerabilities))
            return MonitorStatus.DOWN, latency, 0.0, f"VULNERABILITIES DETECTED: {', '.join(unique)}"
            
        return MonitorStatus.UP, latency, 0.0, f"Secure: Audited {len(visited_urls)} locations. No leaks found."

    async def _probe_sensitive_file(self, url: str) -> Optional[str]:
        """Probing with strict content verification"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MatEl-Auditor/5.0'}
            async with self.session.get(url, timeout=5, allow_redirects=False, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    text = content.decode('utf-8', errors='ignore').lower()
                    
                    is_leak = False
                    if '.env' in url and ('app_' in text or 'db_' in text or 'secret' in text or 'key' in text): is_leak = True
                    elif '.git/config' in url and '[core]' in text: is_leak = True
                    elif 'phpinfo' in url and 'php version' in text: is_leak = True
                    elif response.headers.get('Content-Type', '').lower() != 'text/html' and len(content) > 10: is_leak = True
                    
                    if is_leak:
                        return f"{urlparse(url).path} [SENSITIVE LEAK]"
            return None
        except: return None

    async def check_phishing_radar(self, target: str) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Phishing Radar (Typosquatting / Domain Mimicry Detection)
        """
        import socket
        
        # Clean the target (remove http/https and paths)
        clean_domain = target.replace('https://', '').replace('http://', '').split('/')[0]
        if not clean_domain:
            return MonitorStatus.DOWN, 0.0, 0.0, "Invalid Domain for Phishing Radar"

        domain_parts = clean_domain.rsplit('.', 1)
        if len(domain_parts) < 2:
            return MonitorStatus.DOWN, 0.0, 0.0, "Invalid Domain Format"
            
        name, tld = domain_parts
        start_time = time.time()
        
        # 1. Generate Typosquatting Variations
        variations = []
        # Omission
        for i in range(len(name)):
            variations.append(name[:i] + name[i+1:] + "." + tld)
        # Addition
        characters = 'abcdefghijklmnopqrstuvwxyz0123456789-'
        for i in range(len(name) + 1):
            for char in characters:
                variations.append(name[:i] + char + name[i:] + "." + tld)
        # Transposition
        for i in range(len(name) - 1):
            variations.append(name[:i] + name[i+1] + name[i] + name[i+2:] + "." + tld)
        # Replacement (Visual Similarity / Homoglyphs - simplified)
        replacements = {'o': '0', 'l': '1', 'i': '1', 's': '5', 'a': '4', 'e': '3'}
        for i, char in enumerate(name):
            if char in replacements:
                variations.append(name[:i] + replacements[char] + name[i+1:] + "." + tld)
        
        # Bitsquatting
        for i in range(len(name)):
            char_code = ord(name[i])
            for b in range(8):
                bit_variant = chr(char_code ^ (1 << b))
                if bit_variant in characters:
                    variations.append(name[:i] + bit_variant + name[i+1:] + "." + tld)

        # Filter unique and remove original
        target_variations = list(set(variations))
        if clean_domain in target_variations: target_variations.remove(clean_domain)
        
        # Limit to top 50 highly probable variations for performance
        target_variations = target_variations[:50]

        detected_phishing = []

        async def check_dns(domain):
            try:
                # Use non-blocking DNS resolution
                loop = asyncio.get_event_loop()
                await loop.getaddrinfo(domain, 80)
                return domain
            except:
                return None

        # Execute DNS checks in parallel
        dns_tasks = [check_dns(v) for v in target_variations]
        dns_results = await asyncio.gather(*dns_tasks)
        
        detected_phishing = [d for d in dns_results if d is not None]

        latency = (time.time() - start_time) * 1000
        
        if detected_phishing:
            msg = f"PHISHING ALERT: Potential mimic domains detected: {', '.join(detected_phishing)}"
            return MonitorStatus.DOWN, latency, 0.0, msg
            
        return MonitorStatus.UP, latency, 0.0, f"Radar Clear: Scanned {len(target_variations)} variations. No mimics active."

    async def check_eco_audit(self, target: str) -> Tuple[MonitorStatus, Optional[float], float, Optional[str]]:
        """
        Green-Ops & Cost Intelligence (ECO Audit)
        Analyzes page efficiency, transfer size, and carbon footprint.
        """
        start_time = time.time()
        try:
            # Standardization of URL
            url = target if target.startswith(('http://', 'https://')) else 'https://' + target
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MatEl-EcoAuditor/1.0',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            
            # Disable auto_decompress to measure exactly what's sent over the wire (ECO impact)
            async with self.session.get(url, timeout=10, headers=headers, auto_decompress=False) as response:
                content = await response.read()
                size_bytes = len(content)
                size_kb = size_bytes / 1024
                
                # 1. Carbon Footprint Calculation (Rough estimate: ~0.8g CO2 per MB transferred)
                # Source: Sustainable Web Design / Digital Beacon estimates
                co2_grams = (size_bytes / (1024 * 1024)) * 0.8
                
                # 2. Efficiency Check
                compression = response.headers.get('Content-Encoding', 'none')
                is_compressed = compression in ['gzip', 'br', 'deflate']
                
                # 3. Efficiency Score (0-100)
                # Components: Size penalty, Compression bonus, Latency penalty
                score = 100
                if size_kb > 2000: score -= 30 # Over 2MB is heavy
                elif size_kb > 1000: score -= 15 # Over 1MB
                
                if not is_compressed: score -= 20 # No compression is bad for ECO
                
                latency = (time.time() - start_time) * 1000
                if latency > 1000: score -= 10
                
                status = MonitorStatus.UP
                if score < 40:
                    advice = "🛑 EXTREMELY INEFFICIENT: Huge page size and no compression detected. High hosting costs and carbon footprint!"
                elif score < 70:
                    advice = "⚠️ MODERATE EFFICIENCY: Consider optimizing images and enabling Brotli/Gzip compression."
                else:
                    advice = "🍀 ECO-FRIENDLY: Great job! The page is lightweight and well-compressed."

                eco_data = f"ECO_DATA|Score:{score}|Size:{round(size_kb)}KB|CO2:{co2_grams:.4f}g|Comp:{compression}|Advice:{advice}"
                
                return status, latency, 0.0, eco_data

        except Exception as e:
            return MonitorStatus.DOWN, None, 0.0, f"Eco-Audit Failed: {str(e)}"

    async def check_monitor(self, monitor_id: int, monitor_type: MonitorType, target: str, expected_hash: Optional[str] = None, expected_ports: Optional[str] = None) -> HeartbeatCreate:
        """
        Perform a single check on a monitor
        Returns: HeartbeatCreate object ready to be saved
        """
        if monitor_type == MonitorType.HTTP:
            status, latency, loss, error = await self.check_http(target, expected_hash=expected_hash)
        elif monitor_type == MonitorType.ICMP:
            status, latency, loss, error = await self.check_icmp(target)
        elif monitor_type == MonitorType.SSL:
            status, latency, loss, error = await self.check_ssl(target)
        elif monitor_type == MonitorType.PORT:
            status, latency, loss, error = await self.check_port_scan(target, expected_ports=expected_ports)
        elif monitor_type == MonitorType.GHOST:
            status, latency, loss, error = await self.check_ghost_paths(target)
        elif monitor_type == MonitorType.PHISHING:
            status, latency, loss, error = await self.check_phishing_radar(target)
        elif monitor_type == MonitorType.ECO_AUDIT:
            status, latency, loss, error = await self.check_eco_audit(target)
        else:
            status, latency, loss, error = MonitorStatus.UNKNOWN, None, 0.0, "Unknown monitor type"
        
        return HeartbeatCreate(
            monitor_id=monitor_id,
            status=status,
            latency=latency,
            packet_loss=loss,
            error_message=error
        )
    
    async def check_multiple_monitors(self, monitors: list) -> list[HeartbeatCreate]:
        """
        Check multiple monitors concurrently
        monitors: List of tuples (monitor_id, monitor_type, target, expected_hash, expected_ports)
        Returns: List of HeartbeatCreate objects
        """
        tasks = [
            self.check_monitor(monitor_id, monitor_type, target, expected_hash=expected_hash, expected_ports=expected_ports)
            for monitor_id, monitor_type, target, expected_hash, expected_ports in monitors
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        heartbeats = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Monitor check failed: {result}")
                # Create a DOWN heartbeat for failed checks
                monitor_id, _, _, _, _ = monitors[i]
                heartbeats.append(HeartbeatCreate(
                    monitor_id=monitor_id,
                    status=MonitorStatus.DOWN,
                    latency=None,
                    packet_loss=100.0,
                    error_message=str(result)
                ))
            else:
                heartbeats.append(result)
        
        return heartbeats


# Global monitoring engine instance
monitoring_engine = MonitoringEngine()
