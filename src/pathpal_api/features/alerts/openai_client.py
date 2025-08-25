"""OpenAI client for audio transcription and emergency analysis."""

import asyncio
from io import BytesIO

import httpx
from openai import AsyncOpenAI

from ...settings import settings
from .exceptions import AnalysisError, TranscriptionError


class OpenAIAlertClient:
    """Async OpenAI client for audio transcription and emergency analysis."""

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        """Initialize OpenAI client with optional HTTP client."""
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client,
        )

    async def transcribe_audio(self, audio_data: bytes, filename: str) -> str:
        """Transcribe audio using OpenAI Whisper API.

        Args:
            audio_data: Raw audio file bytes
            filename: Original filename for OpenAI API

        Returns:
            Transcribed text from the audio

        Raises:
            TranscriptionError: If transcription fails or times out
        """
        try:
            # Create file-like object from bytes
            audio_file = BytesIO(audio_data)
            audio_file.name = filename  # OpenAI requires filename attribute

            response = await asyncio.wait_for(
                self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",  # Can be made configurable
                    response_format="text",
                ),
                timeout=30.0,  # 30 second timeout
            )

            return response.strip() if response else ""

        except TimeoutError:
            raise TranscriptionError("Audio transcription timed out")
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {str(e)}")

    async def analyze_emergency_transcript(self, transcript: str) -> str:
        """Analyze emergency transcript using GPT for situation assessment.

        Args:
            transcript: Transcribed audio text

        Returns:
            AI analysis of the emergency situation

        Raises:
            AnalysisError: If analysis fails or times out
        """
        if not transcript or transcript.strip() == "":
            return "The situation is unclear from the audio."

        prompt = self._create_analysis_prompt(transcript)

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Optimized for speed and cost
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a security expert analyzing emergency audio.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=100,
                    temperature=0.1,  # Low temperature for consistent analysis
                ),
                timeout=10.0,  # 10 second timeout
            )

            return response.choices[0].message.content.strip()

        except TimeoutError:
            raise AnalysisError("Emergency analysis timed out")
        except Exception as e:
            raise AnalysisError(f"Analysis failed: {str(e)}")

    def _create_analysis_prompt(self, transcript: str) -> str:
        """Create optimized prompt for emergency analysis."""
        return f"""
You are a security expert analyzing an audio transcript from a user's emergency alert.
Your task is to provide a concise, one-sentence summary of the situation for an emergency contact.
Do not be conversational. Be direct and factual.
Focus on signs of distress, key words (like "help," "stop," "go away"), and any contextual clues (like "he's following me," "I'm near the library").
If the audio is unclear or benign (e.g., background noise, pocket dial), state that "The situation is unclear from the audio."

Transcript: "{transcript}"

One-sentence summary:
"""
