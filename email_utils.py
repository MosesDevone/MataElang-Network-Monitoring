import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from typing import List
from dotenv import load_dotenv

# Pastikan load_dotenv() menimpa env system jika ada perubahan
load_dotenv(override=True)

# Konfigurasi Gmail
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER if SMTP_USER else "noreply@example.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))

# Auto-detect security protocol based on port
# Port 465 uses SSL, Port 587 uses TLS (STARTTLS)
USE_SSL = True if SMTP_PORT == 465 else False
USE_TLS = True if SMTP_PORT == 587 else False

conf = ConnectionConfig(
    MAIL_USERNAME=SMTP_USER,
    MAIL_PASSWORD=SMTP_PASSWORD,
    MAIL_FROM=SMTP_FROM,
    MAIL_PORT=SMTP_PORT,
    MAIL_SERVER=SMTP_SERVER,
    MAIL_STARTTLS=USE_TLS,
    MAIL_SSL_TLS=USE_SSL,
    USE_CREDENTIALS=True if SMTP_USER and SMTP_PASSWORD else False,
    VALIDATE_CERTS=True
)

async def send_verification_email(email: EmailStr, token: str):
    """
    Kirim email verifikasi ke user baru.
    """
    # Menggunakan port 8000 agar sesuai dengan versi EXE/Produksi
    verification_link = f"http://localhost:8000/verify?token={token}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #3b82f6;">MatEl</h1>
                <p style="color: #666;">Eagle Eye Monitoring System</p>
            </div>
            <h2 style="color: #333;">Welcome to the NOC!</h2>
            <p style="color: #555; line-height: 1.6;">
                Thank you for registering. To ensure the security of our network monitoring system, 
                we need to verify your email address.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_link}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    Verify Account
                </a>
            </div>
            <p style="color: #999; font-size: 12px; text-align: center;">
                If you did not request this registration, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Verify Your MatEl Account",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


async def send_reset_password_email(email: EmailStr, token: str):
    """
    Kirim email reset password.
    """
    # Link ke frontend reset password page
    reset_link = f"http://localhost:8000/#reset-password?token={token}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #ef4444;">MatEl</h1>
                <p style="color: #666;">Security Alert</p>
            </div>
            <h2 style="color: #333;">Password Reset Request</h2>
            <p style="color: #555; line-height: 1.6;">
                We received a request to reset your password. If this was you, please click the button below to proceed.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #ef4444; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    Reset Password
                </a>
            </div>
            <p style="color: #999; font-size: 12px; text-align: center;">
                If you did not request a password reset, please ignore this email immediately. Your account is safe.
            </p>
        </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Reset Your MatEl Password",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"❌ Failed to send reset email: {e}")
        return False


async def send_username_email(email: EmailStr, username: str):
    """
    Kirim email berisi username.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #3b82f6;">MatEl</h1>
                <p style="color: #666;">Account Recovery</p>
            </div>
            <h2 style="color: #333;">Your Username</h2>
            <p style="color: #555; line-height: 1.6;">
                You requested to retrieve your username. Here it is:
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <div style="background-color: #f3f4f6; color: #333; padding: 12px 24px; border-radius: 5px; font-weight: bold; font-size: 20px; display: inline-block; border: 1px solid #e5e7eb;">
                    {username}
                </div>
            </div>
            <p style="color: #999; font-size: 12px; text-align: center;">
                If you did not request this, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Your MatEl Username",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"❌ Failed to send username email: {e}")
        return False
