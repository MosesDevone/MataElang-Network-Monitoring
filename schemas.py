from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from models import MonitorType, MonitorStatus, UserRole


# --- User Schemas ---
# Digunakan untuk validasi input Login/Signup
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    role: UserRole
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserUpdate(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# --- Monitor Schemas ---
# Digunakan untuk input Create/Update Monitor
class MonitorBase(BaseModel):
    name: str # wajib
    type: MonitorType # wajib
    target: str # wajib
    interval: int = 60 # default 60
    is_public: bool = False
    expected_hash: Optional[str] = None
    expected_ports: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None

class MonitorCreate(MonitorBase):
    pass

class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[MonitorType] = None
    target: Optional[str] = None
    interval: Optional[int] = None
    is_public: Optional[bool] = None
    expected_hash: Optional[str] = None
    expected_ports: Optional[str] = None

class Monitor(MonitorBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Kita tidak include heartbeats list disini agar response ringan

    model_config = ConfigDict(from_attributes=True)

# Alias for compatibility
MonitorResponse = Monitor


class BulkDeleteRequest(BaseModel):
    ids: List[int]


# --- Heartbeat Schemas ---
# Digunakan untuk mencatat hasil ping/check
class HeartbeatBase(BaseModel):
    status: MonitorStatus
    latency: Optional[float] = None
    packet_loss: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = None  # Optional agar bisa diisi backend jika kosong

class HeartbeatCreate(HeartbeatBase):
    monitor_id: int # Wajib ada!
    
    model_config = ConfigDict(from_attributes=True)

class Heartbeat(HeartbeatBase):
    id: int
    monitor_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# Alias for compatibility
HeartbeatResponse = Heartbeat


# --- Stats & Dashboard Schemas ---
# Digunakan untuk data olahan Dashboard

class MonitorWithStats(Monitor):
    current_status: MonitorStatus
    uptime_percentage: float
    average_latency: Optional[float]
    latest_latency: Optional[float] = None
    average_packet_loss: float = 0.0
    last_check: Optional[datetime]
    last_error: Optional[str] = None

class UptimeStats(BaseModel):
    monitor_id: int
    monitor_name: str
    uptime_percentage: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    average_latency: Optional[float]
    latest_latency: Optional[float] = None
    average_packet_loss: float
    current_status: MonitorStatus
    last_check: Optional[datetime]
    last_error: Optional[str] = None

class IncidentEvent(BaseModel):
    monitor_id: int
    monitor_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    is_ongoing: bool = False

class LatencyData(BaseModel):
    timestamp: datetime
    latency: Optional[float]
    packet_loss: float = 0.0

# --- Speedtest Schemas ---
class SpeedtestResultBase(BaseModel):
    download_speed: float
    upload_speed: float
    ping: float
    isp: Optional[str] = None
    share_url: Optional[str] = None

class SpeedtestResultCreate(SpeedtestResultBase):
    pass

class SpeedtestResult(SpeedtestResultBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# Alias for compatibility
SpeedtestResponse = SpeedtestResult


# --- Traffic Hit Schemas ---
class TrafficHitBase(BaseModel):
    monitor_id: int
    src_ip: Optional[str] = None
    src_lat: Optional[float] = None
    src_lng: Optional[float] = None
    src_country: Optional[str] = None
    src_city: Optional[str] = None
    timestamp: Optional[datetime] = None

class TrafficHitCreate(TrafficHitBase):
    pass

class TrafficHit(TrafficHitBase):
    id: int
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
