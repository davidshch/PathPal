"""Tests for OpenAI client with comprehensive mocking."""

from unittest.mock import AsyncMock, patch

import pytest

from pathpal_api.features.alerts.exceptions import AnalysisError, TranscriptionError
from pathpal_api.features.alerts.openai_client import OpenAIAlertClient


@pytest.fixture
def audio_data():
    """Sample audio data for testing."""
    return b"fake_audio_data_for_testing"


@pytest.mark.asyncio
class TestOpenAIAlertClient:
    """Test suite for OpenAI integration."""

    async def test_transcribe_audio_success(self, audio_data):
        """Test successful audio transcription."""
        client = OpenAIAlertClient()

        with patch.object(
            client.client.audio.transcriptions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "Help, someone is following me near the library!"

            result = await client.transcribe_audio(audio_data, "test.wav")

            assert result == "Help, someone is following me near the library!"
            mock_create.assert_called_once()

    async def test_transcribe_audio_timeout(self, audio_data):
        """Test transcription timeout handling."""
        client = OpenAIAlertClient()

        with patch.object(
            client.client.audio.transcriptions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = TimeoutError()

            with pytest.raises(TranscriptionError, match="timed out"):
                await client.transcribe_audio(audio_data, "test.wav")

    async def test_transcribe_audio_api_error(self, audio_data):
        """Test transcription API error handling."""
        client = OpenAIAlertClient()

        with patch.object(
            client.client.audio.transcriptions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(TranscriptionError, match="Transcription failed"):
                await client.transcribe_audio(audio_data, "test.wav")

    async def test_transcribe_audio_empty_response(self, audio_data):
        """Test transcription with empty response."""
        client = OpenAIAlertClient()

        with patch.object(
            client.client.audio.transcriptions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = ""

            result = await client.transcribe_audio(audio_data, "test.wav")

            assert result == ""

    async def test_analyze_emergency_transcript_success(self):
        """Test successful emergency analysis."""
        client = OpenAIAlertClient()
        transcript = "Help, someone is following me!"

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[
                0
            ].message.content = "User reports being followed - immediate assistance needed."
            mock_create.return_value = mock_response

            result = await client.analyze_emergency_transcript(transcript)

            assert "being followed" in result
            mock_create.assert_called_once()

    async def test_analyze_empty_transcript(self):
        """Test analysis with empty transcript."""
        client = OpenAIAlertClient()

        result = await client.analyze_emergency_transcript("")

        assert result == "The situation is unclear from the audio."

    async def test_analyze_whitespace_only_transcript(self):
        """Test analysis with whitespace-only transcript."""
        client = OpenAIAlertClient()

        result = await client.analyze_emergency_transcript("   \n\t  ")

        assert result == "The situation is unclear from the audio."

    async def test_analyze_emergency_transcript_timeout(self):
        """Test analysis timeout handling."""
        client = OpenAIAlertClient()
        transcript = "Help me!"

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = TimeoutError()

            with pytest.raises(AnalysisError, match="timed out"):
                await client.analyze_emergency_transcript(transcript)

    async def test_analyze_emergency_transcript_api_error(self):
        """Test analysis API error handling."""
        client = OpenAIAlertClient()
        transcript = "Help me!"

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(AnalysisError, match="Analysis failed"):
                await client.analyze_emergency_transcript(transcript)

    async def test_create_analysis_prompt(self):
        """Test analysis prompt creation."""
        client = OpenAIAlertClient()
        transcript = "Help, I'm being followed!"

        prompt = client._create_analysis_prompt(transcript)

        assert transcript in prompt
        assert "security expert" in prompt.lower()
        assert "one-sentence summary" in prompt.lower()
        assert "emergency alert" in prompt.lower()

    async def test_transcribe_audio_with_different_filenames(self, audio_data):
        """Test transcription with different filename formats."""
        client = OpenAIAlertClient()
        test_filenames = ["audio.wav", "emergency.mp3", "alert.webm"]

        with patch.object(
            client.client.audio.transcriptions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "Test transcription"

            for filename in test_filenames:
                result = await client.transcribe_audio(audio_data, filename)
                assert result == "Test transcription"

    async def test_full_workflow_success(self, audio_data):
        """Test complete workflow from transcription to analysis."""
        client = OpenAIAlertClient()

        # Mock transcription
        with patch.object(
            client.client.audio.transcriptions, "create", new_callable=AsyncMock
        ) as mock_transcribe:
            mock_transcribe.return_value = "Someone is following me, I need help!"

            # Mock analysis
            with patch.object(
                client.client.chat.completions, "create", new_callable=AsyncMock
            ) as mock_analyze:
                mock_response = AsyncMock()
                mock_response.choices = [AsyncMock()]
                mock_response.choices[
                    0
                ].message.content = "User is being followed and needs immediate help."
                mock_analyze.return_value = mock_response

                # Execute full workflow
                transcript = await client.transcribe_audio(audio_data, "test.wav")
                analysis = await client.analyze_emergency_transcript(transcript)

                assert transcript == "Someone is following me, I need help!"
                assert "being followed" in analysis
                assert "immediate help" in analysis
