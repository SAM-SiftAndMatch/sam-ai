from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("sam_ai.llm")


class LLMService:
    """Pluggable generative LLM service for prompt completion and synthesis."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.model = model or settings.LLM_MODEL
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY
        self.temperature = (
            temperature if temperature is not None else settings.LLM_TEMPERATURE
        )
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self.timeout = timeout or settings.LLM_TIMEOUT

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
    ) -> str:
        """Send chat messages to the configured LLM provider and return response text."""
        if self.provider == "ollama":
            return await self._chat_ollama(
                system_prompt, user_message, json_mode=json_mode
            )
        elif self.provider == "gemini":
            return await self._chat_gemini(
                system_prompt, user_message, json_mode=json_mode
            )
        elif self.provider == "openai":
            return await self._chat_openai(
                system_prompt, user_message, json_mode=json_mode
            )
        else:
            raise ValueError(f"Unsupported LLM provider: '{self.provider}'")

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Send chat request and parse output as valid JSON."""
        raw_text = await self.chat(system_prompt, user_message, json_mode=True)
        return self._extract_json(raw_text)

    async def _chat_ollama(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
            except httpx.HTTPError as exc:
                logger.error("Ollama request failed: %s", exc)
                raise RuntimeError(f"Ollama LLM call failed: {exc}") from exc

    async def _chat_gemini(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
    ) -> str:
        if not self.api_key:
            raise ValueError("LLM_API_KEY is required for Gemini provider")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=body)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except httpx.HTTPError as exc:
                logger.error("Gemini API request failed: %s", exc)
                raise RuntimeError(f"Gemini LLM call failed: {exc}") from exc

    async def _chat_openai(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
    ) -> str:
        headers = {"Authorization": f"Bearer {self.api_key or ''}"}
        url = f"{self.base_url}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.HTTPError as exc:
                logger.error("OpenAI API request failed: %s", exc)
                raise RuntimeError(f"OpenAI LLM call failed: {exc}") from exc

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Strip markdown fences if any and parse json object."""
        cleaned = text.strip()
        # Remove ```json ... ``` wrapper
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        elif cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse JSON from LLM output: %s\nRaw output: %s", exc, text
            )
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
