"""Core alert processing service with fail-safe logic."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...database.models import Alert, EmergencyContact, User
from .email_service import EmergencyEmailService
from .exceptions import AlertProcessingError
from .openai_client import OpenAIAlertClient

logger = logging.getLogger(__name__)


async def process_emergency_alert(
    db: AsyncSession,
    user: User,
    audio_data: bytes,
    filename: str,
    latitude: float,
    longitude: float,
    openai_client: OpenAIAlertClient,
    email_service: EmergencyEmailService,
) -> dict:
    """Process emergency alert with AI analysis and notifications.

    Args:
        db: Database session
        user: User who triggered the alert
        audio_data: Raw audio file bytes
        filename: Original audio filename
        latitude: User's latitude coordinate
        longitude: User's longitude coordinate
        openai_client: OpenAI client for transcription and analysis
        email_service: Email service for notifications

    Returns:
        Dictionary with processing status and results

    Raises:
        AlertProcessingError: If both AI processing and fallback fail
    """
    timestamp = datetime.now(UTC).isoformat()

    # Get emergency contacts
    emergency_contacts = await _get_user_emergency_contacts(db, user.id)
    if not emergency_contacts:
        raise AlertProcessingError("No emergency contacts configured")

    contact_emails = [contact.contact_email for contact in emergency_contacts]

    try:
        # Step 1: Transcribe audio
        transcript = await openai_client.transcribe_audio(audio_data, filename)
        logger.info(f"Transcribed audio for user {user.id}: {len(transcript)} chars")

        # Step 2: Analyze transcript
        ai_analysis = await openai_client.analyze_emergency_transcript(transcript)
        logger.info(f"AI analysis completed for user {user.id}")

        # Step 3: Send intelligent alert
        await email_service.send_emergency_alert(
            recipient_emails=contact_emails,
            user_name=user.full_name,
            location_lat=latitude,
            location_lon=longitude,
            ai_analysis=ai_analysis,
            timestamp=timestamp,
        )

        # Step 4: Store alert record
        alert = Alert(
            user_id=user.id,
            latitude=latitude,
            longitude=longitude,
            transcript=transcript,
            ai_analysis=ai_analysis,
            contacts_notified=len(contact_emails),
            processing_status="success",
        )
        db.add(alert)
        await db.commit()

        return {
            "status": "success",
            "message": "Emergency alert processed and sent",
            "contacts_notified": len(contact_emails),
            "ai_analysis": ai_analysis,
        }

    except Exception as e:
        logger.error(f"AI processing failed for user {user.id}: {e}")

        # FAIL-SAFE: Send basic alert without AI analysis
        try:
            await email_service.send_fallback_alert(
                recipient_emails=contact_emails,
                user_name=user.full_name,
                location_lat=latitude,
                location_lon=longitude,
                timestamp=timestamp,
            )

            # Store fallback alert record
            alert = Alert(
                user_id=user.id,
                latitude=latitude,
                longitude=longitude,
                transcript="",  # Empty if transcription failed
                ai_analysis="AI processing unavailable",
                contacts_notified=len(contact_emails),
                processing_status="fallback",
                error_details=str(e),
            )
            db.add(alert)
            await db.commit()

            return {
                "status": "fallback",
                "message": "Basic emergency alert sent (AI processing failed)",
                "contacts_notified": len(contact_emails),
                "error": str(e),
            }

        except Exception as fallback_error:
            logger.critical(
                f"Both AI processing and fallback failed for user {user.id}: {fallback_error}"
            )
            raise AlertProcessingError(f"Complete alert processing failure: {fallback_error}")


async def _get_user_emergency_contacts(db: AsyncSession, user_id: UUID) -> list[EmergencyContact]:
    """Get all emergency contacts for a user.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        List of emergency contacts for the user
    """
    statement = select(EmergencyContact).where(EmergencyContact.user_id == user_id)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def get_user_alert_history(db: AsyncSession, user_id: UUID, limit: int = 10) -> list[Alert]:
    """Get alert history for a user.

    Args:
        db: Database session
        user_id: UUID of the user
        limit: Maximum number of alerts to return

    Returns:
        List of user's alerts, most recent first
    """
    statement = (
        select(Alert).where(Alert.user_id == user_id).order_by(Alert.created_at.desc()).limit(limit)
    )
    result = await db.execute(statement)
    return list(result.scalars().all())
