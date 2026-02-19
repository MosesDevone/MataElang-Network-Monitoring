"""
CRUD operations for database
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta
from typing import List, Optional
import models
import schemas


# Monitor CRUD
def create_monitor(db: Session, monitor: schemas.MonitorCreate) -> models.Monitor:
    """Create a new monitor"""
    db_monitor = models.Monitor(**monitor.model_dump())
    db.add(db_monitor)
    db.commit()
    db.refresh(db_monitor)
    return db_monitor


def get_monitor(db: Session, monitor_id: int) -> Optional[models.Monitor]:
    """Get a monitor by ID"""
    return db.query(models.Monitor).filter(models.Monitor.id == monitor_id).first()


def get_monitor_by_name(db: Session, name: str) -> Optional[models.Monitor]:
    """Get a monitor by name"""
    return db.query(models.Monitor).filter(models.Monitor.name == name).first()


def get_monitors(db: Session, skip: int = 0, limit: int = 100) -> List[models.Monitor]:
    """Get all monitors with pagination"""
    return db.query(models.Monitor).offset(skip).limit(limit).all()


def update_monitor(db: Session, monitor_id: int, monitor_update: schemas.MonitorUpdate) -> Optional[models.Monitor]:
    """Update a monitor"""
    db_monitor = get_monitor(db, monitor_id)
    if not db_monitor:
        return None
    
    update_data = monitor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_monitor, field, value)
    
    db_monitor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_monitor)
    return db_monitor


def delete_monitor(db: Session, monitor_id: int) -> bool:
    """Delete a monitor"""
    db_monitor = get_monitor(db, monitor_id)
    if not db_monitor:
        return False
    
    db.delete(db_monitor)
    db.commit()
    return True


def delete_monitors(db: Session, monitor_ids: List[int]) -> int:
    """Bulk delete monitors"""
    deleted_count = db.query(models.Monitor).filter(models.Monitor.id.in_(monitor_ids)).delete(synchronize_session=False)
    db.commit()
    return deleted_count


# Heartbeat CRUD
def create_heartbeat(db: Session, heartbeat: schemas.HeartbeatCreate) -> models.Heartbeat:
    """Create a new heartbeat"""
    db_heartbeat = models.Heartbeat(**heartbeat.model_dump())
    db.add(db_heartbeat)
    db.commit()
    db.refresh(db_heartbeat)
    return db_heartbeat


def get_heartbeats(db: Session, monitor_id: int, hours: int = 24, limit: int = 1000) -> List[models.Heartbeat]:
    """Get heartbeats for a monitor within a time range"""
    since = datetime.utcnow() - timedelta(hours=hours)
    return db.query(models.Heartbeat).filter(
        and_(
            models.Heartbeat.monitor_id == monitor_id,
            models.Heartbeat.timestamp >= since
        )
    ).order_by(desc(models.Heartbeat.timestamp)).limit(limit).all()


def get_latest_heartbeat(db: Session, monitor_id: int) -> Optional[models.Heartbeat]:
    """Get the latest heartbeat for a monitor"""
    return db.query(models.Heartbeat).filter(
        models.Heartbeat.monitor_id == monitor_id
    ).order_by(desc(models.Heartbeat.timestamp)).first()


# Statistics
def get_uptime_stats(db: Session, monitor_id: int, hours: int = 24) -> Optional[schemas.UptimeStats]:
    """Calculate uptime statistics for a monitor"""
    monitor = get_monitor(db, monitor_id)
    if not monitor:
        return None
    
    since = datetime.utcnow() - timedelta(hours=hours)
    heartbeats = db.query(models.Heartbeat).filter(
        and_(
            models.Heartbeat.monitor_id == monitor_id,
            models.Heartbeat.timestamp >= since
        )
    ).order_by(desc(models.Heartbeat.timestamp)).all()
    
    if not heartbeats:
        return schemas.UptimeStats(
            monitor_id=monitor_id,
            monitor_name=monitor.name,
            uptime_percentage=0.0,
            total_checks=0,
            successful_checks=0,
            failed_checks=0,
            average_latency=None,
            average_packet_loss=0.0,
            current_status=models.MonitorStatus.UNKNOWN,
            last_check=None,
            last_error=None
        )
    
    total_checks = len(heartbeats)
    successful_checks = sum(1 for h in heartbeats if h.status == models.MonitorStatus.UP)
    failed_checks = total_checks - successful_checks
    uptime_percentage = (successful_checks / total_checks) * 100 if total_checks > 0 else 0.0
    
    latencies = [h.latency for h in heartbeats if h.latency is not None]
    average_latency = sum(latencies) / len(latencies) if latencies else None
    
    losses = [h.packet_loss for h in heartbeats if h.packet_loss is not None]
    average_packet_loss = sum(losses) / len(losses) if losses else 0.0
    
    latest = heartbeats[0] # Sekarang dijamin yang terbaru karena sudah di-sort desc
    
    return schemas.UptimeStats(
        monitor_id=monitor_id,
        monitor_name=monitor.name,
        uptime_percentage=uptime_percentage,
        total_checks=total_checks,
        successful_checks=successful_checks,
        failed_checks=failed_checks,
        average_latency=average_latency,
        latest_latency=latest.latency,
        average_packet_loss=average_packet_loss,
        current_status=latest.status,
        last_check=latest.timestamp,
        last_error=latest.error_message
    )


def get_latency_history(db: Session, monitor_id: int, hours: int = 1) -> List[schemas.LatencyData]:
    """Get latency history for charts"""
    since = datetime.utcnow() - timedelta(hours=hours)
    heartbeats = db.query(models.Heartbeat).filter(
        and_(
            models.Heartbeat.monitor_id == monitor_id,
            models.Heartbeat.timestamp >= since
        )
    ).order_by(models.Heartbeat.timestamp).all()
    
    return [
        schemas.LatencyData(
            timestamp=h.timestamp,
            latency=h.latency,
            packet_loss=h.packet_loss,
            status=h.status
        )
        for h in heartbeats
    ]


def get_incidents(db: Session, monitor_id: Optional[int] = None, hours: int = 24) -> List[schemas.IncidentEvent]:
    """Get incident timeline - periods when monitors were down"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(models.Heartbeat).filter(
        and_(
            models.Heartbeat.timestamp >= since,
            models.Heartbeat.status == models.MonitorStatus.DOWN
        )
    )
    
    if monitor_id:
        query = query.filter(models.Heartbeat.monitor_id == monitor_id)
    
    query = query.order_by(models.Heartbeat.timestamp)
    down_heartbeats = query.all()
    
    incidents = []
    current_incident = None
    
    for heartbeat in down_heartbeats:
        if current_incident is None:
            # Start new incident
            current_incident = {
                'start_time': heartbeat.timestamp,
                'end_time': None,
                'monitor_id': heartbeat.monitor_id,
                'monitor_name': heartbeat.monitor.name
            }
        elif heartbeat.monitor_id != current_incident['monitor_id']:
            # Different monitor, close current and start new
            incidents.append(schemas.IncidentEvent(
                start_time=current_incident['start_time'],
                end_time=current_incident['end_time'],
                duration_seconds=None,
                monitor_id=current_incident['monitor_id'],
                monitor_name=current_incident['monitor_name'],
                is_ongoing=True
            ))
            current_incident = {
                'start_time': heartbeat.timestamp,
                'end_time': None,
                'monitor_id': heartbeat.monitor_id,
                'monitor_name': heartbeat.monitor.name
            }
        else:
            # Same monitor, update end time
            current_incident['end_time'] = heartbeat.timestamp
    
    # Add final incident if exists
    if current_incident:
        # Check if monitor is back up
        latest = get_latest_heartbeat(db, current_incident['monitor_id'])
        is_ongoing = latest and latest.status == models.MonitorStatus.DOWN
        
        end_time = current_incident['end_time'] or current_incident['start_time']
        duration = int((end_time - current_incident['start_time']).total_seconds()) if current_incident['end_time'] else None
        
        incidents.append(schemas.IncidentEvent(
            start_time=current_incident['start_time'],
            end_time=end_time if not is_ongoing else None,
            duration_seconds=duration,
            monitor_id=current_incident['monitor_id'],
            monitor_name=current_incident['monitor_name'],
            is_ongoing=is_ongoing
        ))
    
    return incidents

def search_monitors(db: Session, query: str) -> List[models.Monitor]:
    """Search monitors by name or target"""
    search_pattern = f"%{query}%"
    return db.query(models.Monitor).filter(
        (models.Monitor.name.like(search_pattern)) |
        (models.Monitor.target.like(search_pattern))
    ).all()


# TrafficHit CRUD
def create_traffic_hit(db: Session, hit: schemas.TrafficHitCreate) -> models.TrafficHit:
    """Create a new traffic hit"""
    db_hit = models.TrafficHit(**hit.model_dump())
    db.add(db_hit)
    db.commit()
    db.refresh(db_hit)
    return db_hit


def get_recent_traffic(db: Session, limit: int = 50) -> List[models.TrafficHit]:
    """Get recent traffic hits"""
    return db.query(models.TrafficHit).order_by(desc(models.TrafficHit.timestamp)).limit(limit).all()
