"""
Notification system for sending alerts
"""
import aiohttp
import os
from typing import Optional
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service untuk mengirim notifikasi melalui berbagai channel
    """
    
    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.enabled = bool(self.telegram_bot_token and self.telegram_chat_id)
    
    async def send_telegram_message(self, message: str) -> bool:
        """
        Send a message via Telegram Bot API
        """
        if not self.enabled:
            logger.warning("Telegram notifications not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Telegram notification sent successfully")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    async def notify_status_change(
        self,
        monitor_name: str,
        old_status: str,
        new_status: str,
        target: str,
        monitor_id: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        Send notification when monitor status changes
        """
        if old_status == new_status:
            return
        
        # Status icons and special headers for Security Anomaly
        is_defaced = error_message and "Integrity Check Failed" in error_message
        is_ghost = error_message and "VULNERABILITY: Sensitive files exposed" in error_message
        is_phishing = error_message and "PHISHING ALERT:" in error_message
        is_eco = error_message and "ECO_DATA|" in error_message
        
        if is_defaced:
            status_icon = "🚨"
            alert_header = "⚠️ *SECURITY ANOMALY DETECTED* 🚨"
        elif is_ghost:
            status_icon = "👻"
            alert_header = "🛑 *GHOST PATH EXPOSURE* 🛑"
        elif is_phishing:
            status_icon = "🎣"
            alert_header = "🚨 *PHISHING RADAR ALERT* 🚨"
        elif is_eco:
            status_icon = "🍃"
            alert_header = "🍀 *ECO-AUDIT COMPLETED* 🍀"
        else:
            status_icon = "🔴" if new_status == "down" else "🟢"
            alert_header = "🦅 *MatEl Alert*"
        
        # Build message
        message = f"""
{alert_header} {status_icon}

*Monitor:* {monitor_name}
*Target:* `{target}`
*Status:* {old_status.upper()} → {new_status.upper()}
*Time:* {self._get_current_time()}
"""
        
        if is_defaced:
            message += f"\n‼️ *SECURITY BREACH:* Content on the target page has been modified without authorization! Baseline integrity check failed."
        elif is_ghost:
            # Parse exposed paths and make them clickable links
            base_url = target.rstrip('/')
            if not base_url.startswith(('http://', 'https://')):
                base_url = 'https://' + base_url
                
            paths_str = error_message.split(': ')[-1]
            paths = [p.strip() for p in paths_str.split(',')]
            
            message += f"\n‼️ *CRITICAL VULNERABILITY:* Sensitive files are publicly accessible! Hacker/Bot can steal your credentials."
            message += f"\n\n*Exposed Files:*"
            for path in paths:
                full_url = base_url + (path if path.startswith('/') else '/' + path)
                message += f"\n🔗 [{path}]({full_url})"
        elif error_message:
            message += f"\n*Error:* {error_message}"
        
        if monitor_id:
            message += f"\n\n🔍 [Detailed here]({self.frontend_url}/details/{monitor_id})"
        
        # Send notification
        await self.send_telegram_message(message)

    async def notify_latency_anomaly(self, monitor_name: str, target: str, average_latency: float, current_latency: float, monitor_id: Optional[int] = None):
        """
        Send an alert when a significant latency spike is detected (DDoS Early Warning)
        """
        status_icon = "⚠️"
        alert_header = "🚨 *DDoS EARLY WARNING* 🚦"
        
        # Calculate increase percentage
        increase = ((current_latency - average_latency) / average_latency) * 100
        
        message = f"""
{alert_header} {status_icon}

*Monitor:* {monitor_name}
*Target:* `{target}`
*Issue:* Unusual Latency Spike Detected!
*Baseline:* {round(average_latency)}ms
*Current:* {round(current_latency)}ms ({round(increase)}% Increase)
*Time:* {self._get_current_time()}

‼️ *POTENTIAL ATTACK:* The server response time has slowed down significantly. This could be an early sign of a DDoS attack or network saturation.
"""
        if monitor_id:
            message += f"\n🔍 [Detailed here]({self.frontend_url}/details/{monitor_id})"
            
        await self.send_telegram_message(message)
    
    async def notify_monitor_down(
        self,
        monitor_name: str,
        target: str,
        monitor_id: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        Quick notification for monitor down event
        """
        await self.notify_status_change(
            monitor_name=monitor_name,
            old_status="up",
            new_status="down",
            target=target,
            monitor_id=monitor_id,
            error_message=error_message
        )
    
    async def notify_monitor_recovered(
        self,
        monitor_name: str,
        target: str,
        monitor_id: Optional[int] = None,
        downtime_seconds: Optional[int] = None
    ):
        """
        Notification for monitor recovery
        """
        message = f"""
🦅 *MatEl Recovery* 🟢

*Monitor:* {monitor_name}
*Target:* `{target}`
*Status:* RECOVERED
*Time:* {self._get_current_time()}
"""
        
        if downtime_seconds:
            minutes = downtime_seconds // 60
            seconds = downtime_seconds % 60
            message += f"\n*Downtime:* {minutes}m {seconds}s"
            
        if monitor_id:
            message += f"\n\n🔍 [Detailed here]({self.frontend_url}/details/{monitor_id})"
        
        await self.send_telegram_message(message)
    
    def _get_current_time(self) -> str:
        """Get current time formatted"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Global notification service instance
notification_service = NotificationService()
