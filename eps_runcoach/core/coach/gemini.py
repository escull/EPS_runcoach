"""Gemini provider for the AI coach, using the official google-genai SDK."""

from __future__ import annotations

from google import genai
from google.genai import errors, types

from eps_runcoach.core.coach.api_key import get_api_key
from eps_runcoach.core.coach.base import CoachConnectionError, CoachError, CoachProvider, CoachRateLimitError


class GeminiProvider(CoachProvider):
    def __init__(self, model: str):
        self.model = model
        api_key = get_api_key()
        if not api_key:
            raise CoachError("No Gemini API key configured - add one on the Settings page.")
        self._client = genai.Client(api_key=api_key)

    def generate_review(self, context: str, system_prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=context,
                config=types.GenerateContentConfig(system_instruction=system_prompt),
            )
        except errors.APIError as exc:
            if exc.code == 429:
                raise CoachRateLimitError("Gemini's rate limit was hit - try again in a minute.") from exc
            raise CoachError(f"Gemini returned an error: {exc.message}") from exc
        except CoachError:
            raise
        except Exception as exc:  # noqa: BLE001 - network/DNS/timeout failures aren't one fixed exception type
            raise CoachConnectionError("Couldn't reach Gemini - check your internet connection.") from exc

        return response.text
