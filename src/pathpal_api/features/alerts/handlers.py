"""FastAPI handlers for emergency alert endpoints."""


from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from ...auth.security import get_current_user
from ...database.connection import get_db
from ...database.models import User
from .email_service import EmergencyEmailService
from .models import AlertHistoryResponse, AlertResponse
from .openai_client import OpenAIAlertClient
from .services import get_user_alert_history, process_emergency_alert

router = APIRouter(prefix="/alerts", tags=["Emergency Alerts"])


# Dependency injection following existing patterns
def get_openai_client() -> OpenAIAlertClient:
    """Get OpenAI client dependency."""
    return OpenAIAlertClient()


def get_email_service() -> EmergencyEmailService:
    """Get email service dependency."""
    return EmergencyEmailService()


@router.post("/emergency", response_model=AlertResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_emergency_alert(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="15-second emergency audio recording"),
    latitude: float = Form(..., ge=-90.0, le=90.0, description="User's precise latitude"),
    longitude: float = Form(..., ge=-180.0, le=180.0, description="User's precise longitude"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    openai_client: OpenAIAlertClient = Depends(get_openai_client),
    email_service: EmergencyEmailService = Depends(get_email_service),
) -> AlertResponse:
    """Process emergency alert with audio analysis and emergency contact notification.

    This endpoint:
    1. Validates the uploaded audio file
    2. Immediately responds to the user (202 Accepted)
    3. Processes the alert in the background with:
       - Audio transcription using OpenAI Whisper
       - Emergency situation analysis using GPT
       - Email notifications to emergency contacts
       - Fail-safe basic alert if AI processing fails

    Args:
        background_tasks: FastAPI background task manager
        audio_file: Uploaded audio file (wav, mp3, mp4, webm formats)
        latitude: User's current latitude (-90 to 90)
        longitude: User's current longitude (-180 to 180)
        current_user: Authenticated user from JWT token
        db: Database session
        openai_client: OpenAI client for transcription and analysis
        email_service: Email service for emergency notifications

    Returns:
        Alert response with processing status and location

    Raises:
        HTTPException: If validation fails or processing setup fails
    """
    # Validate audio file
    if not _is_valid_audio_file(audio_file):
        raise HTTPException(
            status_code=400,
            detail="Invalid audio file. Supported formats: wav, mp3, mp4, mpeg, webm",
        )

    # Read audio data into memory (privacy: no temp files)
    try:
        audio_data = await audio_file.read()
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        if len(audio_data) > 25 * 1024 * 1024:  # 25MB OpenAI limit
            raise HTTPException(status_code=413, detail="Audio file too large (max 25MB)")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Audio file processing error: {str(e)}")

    # Add background task for processing (immediate response to user)
    background_tasks.add_task(
        process_emergency_alert,
        db=db,
        user=current_user,
        audio_data=audio_data,
        filename=audio_file.filename or "emergency_audio.wav",
        latitude=latitude,
        longitude=longitude,
        openai_client=openai_client,
        email_service=email_service,
    )

    # Immediate response - don't make user wait
    return AlertResponse(
        message="Emergency alert received and being processed",
        status="processing",
        user_id=str(current_user.id),
        location={"latitude": latitude, "longitude": longitude},
    )


def _is_valid_audio_file(file: UploadFile) -> bool:
    """Validate audio file type and content.

    Args:
        file: Uploaded file to validate

    Returns:
        True if file is a valid audio format, False otherwise
    """
    if not file.content_type:
        return False

    valid_types = [
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/x-mp3",
        "audio/mp4",
        "audio/x-mp4a",
        "audio/webm",
    ]

    return file.content_type.lower() in valid_types


@router.get("/history", response_model=list[AlertHistoryResponse])
async def get_alert_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlertHistoryResponse]:
    """Get user's alert history for debugging and verification.

    Args:
        limit: Maximum number of alerts to return (default: 10)
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        List of user's alert history, most recent first
    """
    alerts = await get_user_alert_history(db, current_user.id, limit)
    return [AlertHistoryResponse.model_validate(alert) for alert in alerts]
