from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.chunks import get_chunk_service
from app.main import app
from app.models.chunk import ChunkDocument, ChunkMetadata
from app.services.embedding_service import EmbeddingService

client = TestClient(app)


@pytest.mark.asyncio
async def test_embedding_service_mocked():
    service = EmbeddingService(
        base_url="http://localhost:11434", model="bge-m3", dimensions=1024
    )
    fake_vector = [0.1] * 1024

    with patch("httpx.AsyncClient.post") as mock_post:
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {"embeddings": [fake_vector]}
        mock_post.return_value = mock_resp

        vec = await service.get_embedding("test text")
        assert len(vec) == 1024
        assert vec[0] == 0.1


def test_search_endpoint():
    mock_service = AsyncMock()

    # Mock universal chunks
    mock_universal = ChunkDocument(
        id="uni-1",
        text="Universal Content",
        metadata=ChunkMetadata(
            source_file="test.md",
            title="A1",
            breadcrumb="Section > A1",
            always_include=True,
            scope="universal",
        ),
    )
    mock_service.get_universal_chunks.return_value = [mock_universal]

    # Mock search results
    mock_service.semantic_search.return_value = [
        {
            "id": "rel-1",
            "text": "E-commerce Payment Content",
            "metadata": ChunkMetadata(
                source_file="test.md",
                title="B1.2",
                breadcrumb="E-Commerce > B1.2",
                category="website_ban_hang",
            ).model_dump(),
            "score": 0.885,
        }
    ]

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.post(
            "/api/v1/chunks/search",
            json={
                "query": "cần tích hợp cổng thanh toán vnpay",
                "category": "website_ban_hang",
                "limit": 3,
                "include_universal": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "cần tích hợp cổng thanh toán vnpay"
        assert len(data["universal"]) == 1
        assert data["universal"][0]["id"] == "uni-1"
        assert len(data["relevant_chunks"]) == 1
        assert data["relevant_chunks"][0]["id"] == "rel-1"
        assert data["relevant_chunks"][0]["score"] == 0.885
        assert data["total_relevant"] == 1
    finally:
        app.dependency_overrides.clear()


def test_context_endpoint():
    mock_service = AsyncMock()

    mock_universal = ChunkDocument(
        id="uni-1",
        text="Universal Content",
        metadata=ChunkMetadata(
            source_file="test.md",
            title="A1",
            breadcrumb="Section > A1",
            always_include=True,
            scope="universal",
        ),
    )
    mock_cat = ChunkDocument(
        id="cat-1",
        text="Category Content",
        metadata=ChunkMetadata(
            source_file="test.md",
            title="B1",
            breadcrumb="Section > B1",
            category="website_ban_hang",
        ),
    )
    mock_service.get_brief_context.return_value = ([mock_universal], [mock_cat])

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.get("/api/v1/chunks/context?category=website_ban_hang")
        assert response.status_code == 200
        data = response.json()
        assert len(data["universal"]) == 1
        assert len(data["category_specific"]) == 1
        assert data["universal"][0]["id"] == "uni-1"
        assert data["category_specific"][0]["id"] == "cat-1"
    finally:
        app.dependency_overrides.clear()
