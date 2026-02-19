import io
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import List, Optional
import asyncio
import logging
from jose import JWTError, jwt
import json

import models
import schemas
import crud
import auth
from database import engine, get_db
from monitoring import monitoring_engine
from notifications import notification_service
import net_tools

# Auth Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency to get current user
def get_current_user(token = Depends(oauth2_scheme), db = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_head_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.HEAD_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires Head Admin privileges"
        )
    return current_user

def get_current_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.HEAD_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires Admin privileges"
        )
    return current_user


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()


# Background monitoring task
monitoring_task = None
traffic_task = None
previous_statuses = {}  # Track previous statuses for change detection


async def traffic_simulation_loop():
    """
    Simulasi traffic pengunjung global untuk visualisasi real-time
    """
    logger.info("Starting satellite traffic intercept simulation...")
    import random
    
    # Koordinat kota-kota besar dunia untuk simulasi source traffic
    major_cities = [
        {"city": "New York", "country": "USA", "lat": 40.7128, "lng": -74.0060},
        {"city": "London", "country": "UK", "lat": 51.5074, "lng": -0.1278},
        {"city": "Tokyo", "country": "Japan", "lat": 35.6762, "lng": 139.6503},
        {"city": "Sydney", "country": "Australia", "lat": -33.8688, "lng": 151.2093},
        {"city": "Berlin", "country": "Germany", "lat": 52.5200, "lng": 13.4050},
        {"city": "Paris", "country": "France", "lat": 48.8566, "lng": 2.3522},
        {"city": "Moscow", "country": "Russia", "lat": 55.7558, "lng": 37.6173},
        {"city": "Singapore", "country": "Singapore", "lat": 1.3521, "lng": 103.8198},
        {"city": "Jakarta", "country": "Indonesia", "lat": -6.2088, "lng": 106.8456},
        {"city": "Dubai", "country": "UAE", "lat": 25.2048, "lng": 55.2708},
        {"city": "Sao Paulo", "country": "Brazil", "lat": -23.5505, "lng": -46.6333},
        {"city": "Cape Town", "country": "South Africa", "lat": -33.9249, "lng": 18.4241}
    ]

    while True:
        db = None
        try:
            db_gen = get_db()
            db = next(db_gen)
            monitors = crud.get_monitors(db)
            
            # Filter monitors that have location data
            located_monitors = [m for m in monitors if m.latitude and m.longitude]
            
            if located_monitors:
                # Pilih monitor acak untuk menerima traffic
                target_monitor = random.choice(located_monitors)
                source = random.choice(major_cities)
                
                # Buat traffic hit
                hit_data = schemas.TrafficHitCreate(
                    monitor_id=target_monitor.id,
                    src_ip=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                    src_lat=source["lat"],
                    src_lng=source["lng"],
                    src_country=source["country"],
                    src_city=source["city"]
                )
                
                # Simpan ke DB
                hit = crud.create_traffic_hit(db, hit_data)
                
                # Broadcast ke WebSocket
                await manager.broadcast(json.dumps({
                    "type": "traffic",
                    "data": {
                        "id": hit.id,
                        "monitor_id": target_monitor.id,
                        "monitor_name": target_monitor.name,
                        "src_city": source.get("city"),
                        "src_country": source.get("country"),
                        "src_lat": source.get("lat"),
                        "src_lng": source.get("lng"),
                        "target_lat": target_monitor.latitude,
                        "target_lng": target_monitor.longitude,
                        "timestamp": hit.timestamp.isoformat()
                    }
                }))
                
        except Exception as e:
            logger.error(f"Traffic Simulation Error: {e}")
        finally:
            if db: db.close()
            
        # Tunggu antara 2-8 detik untuk hit berikutnya
        await asyncio.sleep(random.uniform(2, 8))


async def monitoring_loop(interval: int = 30):
    """
    Background task yang menjalankan monitoring secara berkala
    """
    global previous_statuses
    
    logger.info("Starting monitoring loop...")
    
    while True:
        db = None
        try:
            # Get database session correctly as a context manager if possible, 
            # or manual next/close with robust error handling
            db_gen = get_db()
            db = next(db_gen)
            
            # Get all monitors
            monitors = crud.get_monitors(db)
            
            if monitors:
                # Prepare monitor data for checking
                monitor_data = [
                    (m.id, m.type, m.target, m.expected_hash, m.expected_ports)
                    for m in monitors
                ]
                
                # Check all monitors concurrently
                heartbeats = await monitoring_engine.check_multiple_monitors(monitor_data)
                
                # Save heartbeats and check for status changes
                for heartbeat_data in heartbeats:
                    monitor_id = heartbeat_data.monitor_id
                    monitor = next((m for m in monitors if m.id == monitor_id), None)
                    if not monitor: continue

                    # Save heartbeat
                    crud.create_heartbeat(db, heartbeat_data)
                    
                    # Check for status change
                    current_status = heartbeat_data.status
                    previous_status = previous_statuses.get(monitor_id)
                    
                    if previous_status and previous_status != current_status:
                        # Status changed - send notification
                        await notification_service.notify_status_change(
                            monitor_name=monitor.name,
                            old_status=previous_status.value,
                            new_status=current_status.value,
                            target=monitor.target,
                            monitor_id=monitor_id,
                            error_message=heartbeat_data.error_message
                        )
                    
                    # Update previous status
                    previous_statuses[monitor_id] = current_status

                    # DDoS Early Warning (Latency Anomaly Detection)
                    if current_status == models.MonitorStatus.UP and heartbeat_data.latency:
                        stats = crud.get_uptime_stats(db, monitor_id)
                        if stats and stats.average_latency:
                            baseline = stats.average_latency
                            current = heartbeat_data.latency
                            
                            # Trigger if latency is > 3x baseline AND baseline is significant (>10ms)
                            # AND current latency is high enough to be an issue (>50ms)
                            if baseline > 10 and current > (baseline * 3) and current > 50:
                                logger.warning(f"DDoS WARNING: Latency spike detected on {monitor.name} ({current}ms vs avg {baseline}ms)")
                                await notification_service.notify_latency_anomaly(
                                    monitor_name=monitor.name,
                                    target=monitor.target,
                                    average_latency=baseline,
                                    current_latency=current,
                                    monitor_id=monitor_id
                                )

                    # GHOST Vulnerability Detection Logging
                    if monitor.type == models.MonitorType.GHOST and heartbeat_data.status == models.MonitorStatus.DOWN:
                         logger.error(f"SECURITY BREACH: {monitor.name} is exposing GHOST paths!")
                
                logger.info(f"Successfully checked {len(monitors)} monitors")
            
        except Exception as e:
            logger.error(f"CRITICAL Error in monitoring loop: {e}")
        finally:
            if db:
                db.close()
                del db # Force cleanup
        
        # Wait before next check
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    global monitoring_task, traffic_task
    
    logger.info("Starting MatEl monitoring system...")
    await monitoring_engine.start()
    
    # Start background monitoring loop
    monitoring_task = asyncio.create_task(monitoring_loop(interval=30))
    
    # Start traffic simulation loop
    traffic_task = asyncio.create_task(traffic_simulation_loop())
    
    yield
    
    # Shutdown
    logger.info("Shutting down MatEl monitoring system...")
    if monitoring_task:
        monitoring_task.cancel()
    
    if traffic_task:
        traffic_task.cancel()
        
    try:
        if monitoring_task: await monitoring_task
        if traffic_task: await traffic_task
    except asyncio.CancelledError:
        pass
    
    await monitoring_engine.stop()


# Create FastAPI app
app = FastAPI(
    title="MatEl - Network Monitoring System",
    description="ISP-grade network monitoring with real-time alerting",
    version="1.0.0",
    lifespan=lifespan
)

# WebSocket Real-time Traffic Endpoints
@app.websocket("/ws/traffic")
async def websocket_traffic(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Tetap buka koneksi, client tidak kirim data cuma terima
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        manager.disconnect(websocket)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



import uuid

import email_utils

# ============================================
# Auth Endpoints
# ============================================

@app.post("/api/auth/signup")
async def signup(user: schemas.UserCreate, background_tasks: BackgroundTasks, db = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_username = db.query(models.User).filter(models.User.username == user.username).first()
    if db_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Generate verification token
    verification_token = str(uuid.uuid4())
    
    # First user becomes HEAD_ADMIN
    user_count = db.query(models.User).count()
    role = models.UserRole.HEAD_ADMIN if user_count == 0 else models.UserRole.USER
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        is_verified=False,
        role=role,
        verification_token=verification_token
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # --- KIRIM EMAIL VERIFIKASI (REAL - ASYNC) ---
    try:
        # Kirim email di background agar user experience cepat
        background_tasks.add_task(email_utils.send_verification_email, user.email, verification_token)
        logging.info(f"📧 Sending verification email to {user.email}...")
        
        # Fallback: Tetap log ke console untuk debugging (opsional)
        print(f"\n[DEV LOG] Verification Link: http://localhost:3000/verify?token={verification_token}\n")
        
    except Exception as e:
        logging.error(f"❌ Failed to enqueue email: {e}")
        # Note: Kita tidak rollback user creation meski email gagal, user bisa minta resend nanti (fitur future)
    
    return {"message": "Registration successful. Please check your email inbox (or spam folder) to verify your account."}

@app.get("/api/auth/verify")
def verify_email(token: str, db = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    user.is_verified = True
    # Kami biarkan token tetap ada sebagai record sejarah (atau hapus nanti lewat cleanup job)
    # Ini mencegah error 400 jika pemanggil memanggil dua kali secara bersamaan
    db.commit()
    
    return {"message": "Email verified successfully. You can now login."}

@app.post("/api/auth/resend-verification")
async def resend_verification(email_data: schemas.UserLogin, background_tasks: BackgroundTasks, db = Depends(get_db)):
    # Biar simpel kita pake UserLogin schema cuma buat ambil 'username' (sebenarnya email)
    logger.info(f"🔄 Resend Verification Request for: {email_data.username}")

    # FIX: Cari berdasarkan EMAIL karena frontend mengirim email di field username
    user = db.query(models.User).filter(models.User.email == email_data.username).first()
    
    # Fallback: Cari berdasarkan username
    if not user:
        user = db.query(models.User).filter(models.User.username == email_data.username).first()

    if not user:
        logger.warning(f"❌ User not found for resend: {email_data.username}")
        raise HTTPException(status_code=404, detail="User not found with this email")
        
    logger.info(f"✅ User found: {user.username} ({user.email}). Queueing email...")
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    background_tasks.add_task(email_utils.send_verification_email, user.email, user.verification_token)
    return {"message": "Verification email resent successfully"}


@app.post("/api/auth/forgot-username")
async def forgot_username(
    request: schemas.PasswordResetRequest, # Reuse schema with email field
    background_tasks: BackgroundTasks, 
    db = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        # Don't reveal user existence
        return {"message": "If this email is registered, your username has been sent."}

    background_tasks.add_task(email_utils.send_username_email, user.email, user.username)
    return {"message": "If this email is registered, your username has been sent."}

@app.post("/api/auth/login")
def login(form_data = Depends(OAuth2PasswordRequestForm), db = Depends(get_db)):
    # Note: OAuth2 form uses 'username' field even for email
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your inbox.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@app.get("/api/auth/me", response_model=schemas.User)
def read_users_me(current_user = Depends(get_current_user)):
    return current_user


@app.put("/api/auth/me/profile", response_model=schemas.User)
def update_user_profile(
    profile_data: schemas.UserUpdate, 
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update own profile (Bio & Avatar)
    """
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url
    
    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/api/auth/forgot-password")
async def forgot_password(
    request: schemas.PasswordResetRequest, 
    background_tasks: BackgroundTasks, 
    db = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        # Don't reveal user existence
        return {"message": "If this email is registered, a password reset link has been sent."}

    # Generate Token
    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    db.commit()

    background_tasks.add_task(email_utils.send_reset_password_email, user.email, reset_token)
    return {"message": "If this email is registered, a password reset link has been sent."}


@app.post("/api/auth/reset-password")
def reset_password(
    confirm: schemas.PasswordResetConfirm, 
    db = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.reset_token == confirm.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Hash new password
    hashed_password = auth.get_password_hash(confirm.new_password)
    user.hashed_password = hashed_password
    user.reset_token = None # Invalidate token
    db.commit()
    
    return {"message": "Password reset successfully. You can now login with your new password."}



# ============================================
# User Management (Head Admin Only)
# ============================================

@app.get("/api/users", response_model=List[schemas.User])
def get_all_users(
    skip: int = 0, 
    limit: int = 100, 
    db = Depends(get_db), 
    current_user = Depends(get_current_head_admin)
):
    """
    List all users (Head Admin Only)
    """
    return db.query(models.User).offset(skip).limit(limit).all()


@app.put("/api/users/{user_id}/role", response_model=schemas.User)
def update_user_role(
    user_id: int, 
    role_update: schemas.UserRoleUpdate,
    db = Depends(get_db), 
    current_user = Depends(get_current_head_admin)
):
    """
    Update user role (Head Admin Only)
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = role_update.role
    db.commit()
    db.refresh(user)
    return user


# ============================================
# Monitor Endpoints
# ============================================

@app.post("/api/monitors", response_model=schemas.MonitorResponse, status_code=201)
async def create_monitor(
    monitor: schemas.MonitorCreate, 
    db = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Create a new monitor
    """
    # Check if monitor with same name exists
    existing = crud.get_monitor_by_name(db, monitor.name)
    if existing:
        raise HTTPException(status_code=400, detail="Monitor with this name already exists")
    
    # Resolve GeoIP (Best Effort)
    try:
        geo_data = await net_tools.resolve_geoip(monitor.target)
        if geo_data:
            monitor.latitude = geo_data.get("latitude")
            monitor.longitude = geo_data.get("longitude")
            monitor.country = geo_data.get("country")
            # We can also store city if we want, but schema does not have it yet.
            # Assuming MonitorCreate respects fields in MonitorBase (which includes lat, lon, country)
    except Exception as e:
        logger.warning(f"Failed to resolve GeoIP for {monitor.target}: {e}")

    db_monitor = crud.create_monitor(db, monitor)
    
    # Trigger first check immediately to avoid UNKNOWN status
    try:
        # Panggil secara langsung karena endpoint ini sudah 'async'
        heartbeat_data = await monitoring_engine.check_monitor(
            monitor_id=db_monitor.id,
            monitor_type=db_monitor.type,
            target=db_monitor.target,
            expected_hash=db_monitor.expected_hash # Tambahan kuncinya disini
        )
        
        crud.create_heartbeat(db, heartbeat_data)
        logger.info(f"Initial check for monitor {db_monitor.name} completed successfully.")
    except Exception as e:
        logger.warning(f"Initial check for monitor {db_monitor.name} failed: {e}")
        
    return db_monitor


@app.get("/api/monitors", response_model=List[schemas.MonitorResponse])
def list_monitors(
    skip: int = 0, 
    limit: int = 100, 
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List all monitors
    """
    return crud.get_monitors(db, skip=skip, limit=limit)


@app.get("/api/monitors/search", response_model=List[schemas.MonitorResponse])
def search_monitors(q: str, db = Depends(get_db)):
    """
    Search monitors by name or target
    """
    return crud.search_monitors(db, q)


@app.get("/api/monitors/{monitor_id}", response_model=schemas.MonitorResponse)
def get_monitor(monitor_id: int, db = Depends(get_db)):
    """
    Get a specific monitor
    """
    monitor = crud.get_monitor(db, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@app.put("/api/monitors/{monitor_id}", response_model=schemas.MonitorResponse)
def update_monitor(
    monitor_id: int,
    monitor_update: schemas.MonitorUpdate,
    db = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Update a monitor
    """
    monitor = crud.update_monitor(db, monitor_id, monitor_update)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@app.delete("/api/monitors/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, db = Depends(get_db), current_user = Depends(get_current_head_admin)):
    """
    Delete a monitor
    """
    success = crud.delete_monitor(db, monitor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return None


@app.post("/api/monitors/bulk-delete")
def bulk_delete_monitors(
    request: schemas.BulkDeleteRequest,
    db = Depends(get_db),
    current_user = Depends(get_current_head_admin)
):
    """
    Delete multiple monitors
    """
    count = crud.delete_monitors(db, request.ids)
    return {"message": f"Successfully deleted {count} monitors"}


# ============================================
# Statistics & Analytics Endpoints
# ============================================

@app.get("/api/monitors/{monitor_id}/stats", response_model=schemas.UptimeStats)
def get_monitor_stats(
    monitor_id: int,
    hours: int = 24,
    db = Depends(get_db)
):
    """
    Get uptime statistics for a monitor
    """
    stats = crud.get_uptime_stats(db, monitor_id, hours=hours)
    if not stats:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return stats


# --- Advanced Tools Endpoints ---

@app.get("/api/reports/sla/{monitor_id}")
def get_sla_report(monitor_id: int, db = Depends(get_db)):
    """Download SLA Report PDF"""
    pdf_buffer = net_tools.generate_sla_report(db, monitor_id)
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=sla_report_{monitor_id}.pdf"}
    )


@app.get("/api/reports/csv/{monitor_id}")
def get_sla_csv(monitor_id: int, db = Depends(get_db)):
    """Download SLA Report CSV"""
    csv_content = net_tools.generate_sla_csv(db, monitor_id)
    return StreamingResponse(
        io.BytesIO(csv_content.encode()), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=sla_report_{monitor_id}.csv"}
    )


@app.get("/api/public/status")
def get_public_status(db = Depends(get_db)):
    """
    Get public status of all monitors (no auth required)
    """
    monitors = db.query(models.Monitor).filter(models.Monitor.is_public == True).all()
    results = []
    for m in monitors:
        # Get 30d stats
        stats = crud.get_uptime_stats(db, m.id, hours=720)
        
        # Get latest status from heartbeats
        latest_hb = crud.get_latest_heartbeat(db, m.id)
        current_status = latest_hb.status if latest_hb else models.MonitorStatus.UNKNOWN
        last_check = latest_hb.timestamp if latest_hb else None

        results.append({
            "id": m.id,
            "name": m.name,
            "type": m.type,
            "target": m.target if m.type == models.MonitorType.HTTP else "", # Mask non-HTTP targets for privacy
            "current_status": current_status,
            "uptime_percentage": round(stats.uptime_percentage, 2) if stats else 0,
            "last_check": last_check
        })
    return results

@app.get("/api/traceroute/{target:path}")
async def get_traceroute(target: str):
    """Run geographical traceroute"""
    return await net_tools.perform_geotraceroute(target)

@app.get("/api/speedtest/run")
async def run_speedtest(db = Depends(get_db)):
    """Run speedtest manual trigger"""
    loop = asyncio.get_event_loop()
    # Run in thread pool because speedtest is blocking
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, net_tools.perform_speedtest)
    
    if "error" not in result:
        # Save to DB
        db_speed = models.SpeedtestResult(
            download_speed=result['download'],
            upload_speed=result['upload'],
            ping=result['ping'],
            isp=result['client']['isp'],
            share_url=result['share']
        )
        db.add(db_speed)
        db.commit()
    
    return result

@app.get("/api/speedtest/history")
def get_speedtest_history(db = Depends(get_db)):
    """Get speedtest history"""
    return db.query(models.SpeedtestResult).order_by(models.SpeedtestResult.timestamp.desc()).limit(20).all()



@app.get("/api/monitors/{monitor_id}/latency", response_model=List[schemas.LatencyData])
def get_latency_history(
    monitor_id: int,
    hours: int = 1,
    db = Depends(get_db)
):
    """
    Get latency history for charts
    """
    monitor = crud.get_monitor(db, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    return crud.get_latency_history(db, monitor_id, hours=hours)


@app.get("/api/monitors/{monitor_id}/heartbeats", response_model=List[schemas.HeartbeatResponse])
def get_monitor_heartbeats(
    monitor_id: int,
    hours: int = 24,
    db = Depends(get_db)
):
    """
    Get heartbeat history
    """
    monitor = crud.get_monitor(db, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    return crud.get_heartbeats(db, monitor_id, hours=hours)


@app.get("/api/dashboard", response_model=List[schemas.MonitorWithStats])
def get_dashboard(
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get dashboard data with all monitors and their current stats
    """
    monitors = crud.get_monitors(db)
    
    dashboard_data = []
    for monitor in monitors:
        stats = crud.get_uptime_stats(db, monitor.id, hours=24)
        
        # Manually combine monitor data and stats
        monitor_data = schemas.Monitor.model_validate(monitor).model_dump()
        
        dashboard_item = schemas.MonitorWithStats(
            **monitor_data,
            current_status=stats.current_status if stats else models.MonitorStatus.UNKNOWN,
            uptime_percentage=stats.uptime_percentage if stats else 0.0,
            average_latency=stats.average_latency if stats else None,
            latest_latency=stats.latest_latency if stats else None,
            average_packet_loss=stats.average_packet_loss if stats else 0.0,
            last_check=stats.last_check if stats else None,
            last_error=stats.last_error if stats else None
        )
        dashboard_data.append(dashboard_item)
        
    return dashboard_data


# ============================================
# Incident Timeline
# ============================================

@app.get("/api/incidents", response_model=List[schemas.IncidentEvent])
def get_incidents(
    monitor_id: Optional[int] = None,
    hours: int = 24,
    db = Depends(get_db)
):
    """
    Get incident timeline - history of downtime events
    """
    return crud.get_incidents(db, monitor_id=monitor_id, hours=hours)


# ============================================
# Manual Check Endpoint
# ============================================

@app.post("/api/monitors/{monitor_id}/check", response_model=schemas.HeartbeatResponse)
async def manual_check(monitor_id: int, db = Depends(get_db)):
    """
    Manually trigger a check for a monitor
    """
    monitor = crud.get_monitor(db, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Perform check
    heartbeat_data = await monitoring_engine.check_monitor(
        monitor_id=monitor.id,
        monitor_type=monitor.type,
        target=monitor.target,
        expected_hash=monitor.expected_hash,
        expected_ports=monitor.expected_ports
    )
    
    # Check for status change vs last known status in global tracking
    current_status = heartbeat_data.status
    previous_status = previous_statuses.get(monitor_id)
    
    if previous_status and previous_status != current_status:
        await notification_service.notify_status_change(
            monitor_name=monitor.name,
            old_status=previous_status.value,
            new_status=current_status.value,
            target=monitor.target,
            error_message=heartbeat_data.error_message
        )
    
    # Update global status tracker
    previous_statuses[monitor_id] = current_status
    
    # Save heartbeat
    heartbeat = crud.create_heartbeat(db, heartbeat_data)
    
    return heartbeat


@app.post("/api/monitors/{monitor_id}/lock-content")
async def lock_content(
    monitor_id: int, 
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lock current website content as a baseline for defacement detection
    """
    import hashlib
    import aiohttp
    
    monitor = crud.get_monitor(db, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
        
    if monitor.type != models.MonitorType.HTTP:
        raise HTTPException(status_code=400, detail="Defacement check is only available for HTTP/HTTPS monitors")
    
    try:
        # Fetch current content
        target = monitor.target
        if not target.startswith(('http://', 'https://')):
            target = f'http://{target}'
            
        async with aiohttp.ClientSession() as session:
            async with session.get(target, timeout=10) as response:
                if response.status >= 200 and response.status < 400:
                    content = await response.read()
                    content_hash = hashlib.sha256(content).hexdigest()
                    
                    # Save hash to database
                    monitor.expected_hash = content_hash
                    db.add(monitor)
                    db.commit()
                    db.refresh(monitor)
                    
                    return {"status": "success", "message": "Content locked successfully", "hash": content_hash}
                else:
                    raise HTTPException(status_code=response.status, detail=f"Target returned HTTP {response.status}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch content: {str(e)}")


# ============================================
# Health Check
# ============================================

@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "MatEl Network Monitoring",
        "version": "1.0.0"
    }


import sys

# ============================================
# Serve Frontend Static Files (Production/EXE)
# ============================================

def get_base_path():
    if getattr(sys, 'frozen', False):
        # Running as EXE
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

base_path = get_base_path()
static_path = os.path.join(base_path, "static")

if os.path.exists(static_path):
    # Mount the 'static/static' folder specifically for assets (js/css)
    # This matches React's default build structure to avoid 404s
    assets_path = os.path.join(static_path, "static")
    if os.path.exists(assets_path):
        app.mount("/static", StaticFiles(directory=assets_path), name="static")
    
    # Catch-all for Root and React Router (SPA)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Exclude API, docs, and health
        if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
            raise HTTPException(status_code=404)
        
        # Check if the requested file exists in the root of static (like manifest.json, favicon)
        file_path = os.path.join(static_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Return index.html for everything else (for React Router support)
        return FileResponse(os.path.join(static_path, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "MatEl API is running. Frontend static files not found."}


@app.post("/api/monitors/{monitor_id}/lock-ports")
async def lock_ports(
    monitor_id: int, 
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lock current open ports as a baseline for security monitoring
    """
    monitor = crud.get_monitor(db, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
        
    try:
        # Perform a fresh port scan to get current open ports
        from monitoring import monitoring_engine
        status, latency, loss, info = await monitoring_engine.check_port_scan(monitor.target)
        
        # Parse open ports from info message
        # Format: "Open ports found: 80,443" or "Open ports found: None"
        ports = ""
        if "Open ports found:" in info:
            ports = info.split("Open ports found:")[1].strip()
            if ports == "None":
                ports = ""
        
        # Save to database
        monitor.expected_ports = ports
        db.add(monitor)
        db.commit()
        db.refresh(monitor)
        
        return {"status": "success", "message": "Baseline ports locked successfully", "ports": ports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan ports: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
