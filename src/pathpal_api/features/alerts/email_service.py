"""Emergency email notification service."""

import logging
from typing import List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from ...settings import settings
from .exceptions import EmailNotificationError

logger = logging.getLogger(__name__)


class EmergencyEmailService:
    """Service for sending emergency alert emails to contacts."""

    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USERNAME,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.SMTP_FROM_EMAIL,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_SERVER,
            MAIL_STARTTLS=settings.SMTP_STARTTLS,
            MAIL_SSL_TLS=settings.SMTP_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER="src/pathpal_api/features/alerts/templates",
        )
        self.fast_mail = FastMail(self.conf)

    async def send_emergency_alert(
        self,
        recipient_emails: List[str],
        user_name: str,
        location_lat: float,
        location_lon: float,
        ai_analysis: str,
        timestamp: str,
    ) -> bool:
        """Send emergency alert emails to all emergency contacts.
        
        Args:
            recipient_emails: List of emergency contact email addresses
            user_name: Full name of the user who triggered alert
            location_lat: User's latitude coordinate
            location_lon: User's longitude coordinate
            ai_analysis: AI-generated situation analysis
            timestamp: ISO timestamp when alert was created
            
        Returns:
            True if email was sent successfully
            
        Raises:
            EmailNotificationError: If email sending fails
        """
        # Generate Google Maps link
        maps_link = f"https://maps.google.com/?q={location_lat},{location_lon}"

        template_data = {
            "user_name": user_name,
            "latitude": location_lat,
            "longitude": location_lon,
            "maps_link": maps_link,
            "ai_analysis": ai_analysis,
            "timestamp": timestamp,
        }

        message = MessageSchema(
            subject=f"🚨 EMERGENCY ALERT - {user_name}",
            recipients=recipient_emails,
            template_body=template_data,
            subtype="html",
        )

        try:
            await self.fast_mail.send_message(
                message, template_name="emergency_alert.html"
            )
            logger.info(
                f"Emergency alert sent to {len(recipient_emails)} contacts for {user_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send emergency alert: {e}")
            raise EmailNotificationError(f"Email notification failed: {str(e)}")

    async def send_fallback_alert(
        self,
        recipient_emails: List[str],
        user_name: str,
        location_lat: float,
        location_lon: float,
        timestamp: str,
    ) -> bool:
        """Send basic alert when AI processing fails.
        
        Args:
            recipient_emails: List of emergency contact email addresses
            user_name: Full name of the user who triggered alert
            location_lat: User's latitude coordinate
            location_lon: User's longitude coordinate
            timestamp: ISO timestamp when alert was created
            
        Returns:
            True if email was sent successfully
            
        Raises:
            EmailNotificationError: If email sending fails
        """
        maps_link = f"https://maps.google.com/?q={location_lat},{location_lon}"

        # Simple fallback message
        html_body = f"""
        <h2>🚨 EMERGENCY ALERT</h2>
        <p><strong>{user_name}</strong> has triggered an emergency alert.</p>
        <p><strong>Time:</strong> {timestamp}</p>
        <p><strong>Location:</strong> <a href="{maps_link}">View on Google Maps</a></p>
        <p><em>Audio analysis was unavailable - please contact immediately.</em></p>
        """

        message = MessageSchema(
            subject=f"🚨 EMERGENCY ALERT - {user_name}",
            recipients=recipient_emails,
            body=html_body,
            subtype="html",
        )

        try:
            await self.fast_mail.send_message(message)
            logger.info(f"Fallback alert sent to {len(recipient_emails)} contacts")
            return True
        except Exception as e:
            logger.error(f"Failed to send fallback alert: {e}")
            raise EmailNotificationError(f"Fallback email failed: {str(e)}")