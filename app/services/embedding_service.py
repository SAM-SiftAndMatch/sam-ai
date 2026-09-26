from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("sam_ai.embedding")


class EmbeddingService:
    """Service to generate dense vector embeddings using Ollama."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        timeout: float = 60.0,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self.timeout = timeout

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a single vector embedding for the input text."""
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Input text cannot be empty.")

        url = f"{self.base_url}/api/embed"
        payload: dict[str, Any] = {
            "model": self.model,
            "input": cleaned_text,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings")
                if not embeddings or not isinstance(embeddings, list):
                    raise ValueError(f"Invalid embedding response structure: {data}")
                return embeddings[0]
        except httpx.ConnectError as e:
            logger.error("Failed to connect to Ollama at %s: %s", self.base_url, e)
            raise RuntimeError(
                f"Cannot connect to Ollama server at {self.base_url}. Ensure Ollama is running."
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "Ollama API error (%s): %s", e.response.status_code, e.response.text
            )
            raise RuntimeError(f"Ollama API returned error: {e.response.text}") from e

    async def get_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 15,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches to prevent payload limits."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        url = f"{self.base_url}/api/embed"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(0, len(texts), batch_size):
                batch = [t.strip() for t in texts[i : i + batch_size]]
                payload: dict[str, Any] = {
                    "model": self.model,
                    "input": batch,
                }
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    batch_res = data.get("embeddings")
                    if not batch_res or len(batch_res) != len(batch):
                        raise ValueError(
                            f"Mismatch in batch embedding count: expected {len(batch)}, got {len(batch_res) if batch_res else 0}"
                        )
                    all_embeddings.extend(batch_res)
                except httpx.ConnectError as e:
                    logger.error(
                        "Connection failed to Ollama at %s: %s", self.base_url, e
                    )
                    raise RuntimeError(
                        f"Cannot connect to Ollama server at {self.base_url}."
                    ) from e
                except httpx.HTTPStatusError as e:
                    logger.error("Ollama error in batch: %s", e.response.text)
                    raise RuntimeError(
                        f"Ollama batch API error: {e.response.text}"
                    ) from e

        return all_embeddings


embedding_service = EmbeddingService()
