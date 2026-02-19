"""
Database models for MatEl monitoring system
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class MonitorType(str, enum.Enum):
    HTTP = "http"
    ICMP = "icmp"
    SSL = "ssl"
    PORT = "port"
    GHOST = "ghost"
    PHISHING = "phishing"
    ECO_AUDIT = "eco_audit"


class MonitorStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    HEAD_ADMIN = "head_admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(Enum(MonitorType), nullable=False)
    target = Column(String, nullable=False)
    interval = Column(Integer, default=60)
    is_public = Column(Boolean, default=False)
    expected_hash = Column(String, nullable=True) # Sidik jari konten web
    expected_ports = Column(String, nullable=True) # Baseline port terbuka (koma terpisah)
    latitude = Column(Float, nullable=True) # GeoIP Data
    longitude = Column(Float, nullable=True) # GeoIP Data
    country = Column(String, nullable=True) # GeoIP Data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    heartbeats = relationship("Heartbeat", back_populates="monitor", cascade="all, delete-orphan")


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id"), nullable=False)
    status = Column(Enum(MonitorStatus), nullable=False)
    latency = Column(Float, nullable=True)
    packet_loss = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    error_message = Column(String, nullable=True)
    
    monitor = relationship("Monitor", back_populates="heartbeats")


class SpeedtestResult(Base):
    __tablename__ = "speedtests"

    id = Column(Integer, primary_key=True, index=True)
    download_speed = Column(Float, nullable=False)
    upload_speed = Column(Float, nullable=False)
    ping = Column(Float, nullable=False)
    isp = Column(String, nullable=True)
    share_url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class TrafficHit(Base):
    __tablename__ = "traffic_hits"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id"), nullable=False)
    src_ip = Column(String, nullable=True)
    src_lat = Column(Float, nullable=True)
    src_lng = Column(Float, nullable=True)
    src_country = Column(String, nullable=True)
    src_city = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    monitor = relationship("Monitor")
