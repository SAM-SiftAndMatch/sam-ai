from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.v1.endpoints.chunks import get_chunk_service
from app.main import app
from app.models.chunk import ChunkDocument, ChunkMetadata
from app.schemas.chunk import ChunkStatsResponse

client = TestClient(app)


def test_chunk_metadata_model():
    # Test keywords parsing from comma-separated string
    meta = ChunkMetadata(
        source_file="test.md",
        title="Test Title",
        breadcrumb="Test > Breadcrumb",
        keywords="kw1, kw2, kw3",
    )
    assert meta.keywords == ["kw1", "kw2", "kw3"]
    assert meta.scope == "category_specific"
    assert meta.always_include is False

    # Test keywords as list
    meta2 = ChunkMetadata(
        source_file="test.md",
        title="Test Title",
        breadcrumb="Test > Breadcrumb",
        keywords=["a", "b"],
        scope="universal",
        always_include=True,
    )
    assert meta2.keywords == ["a", "b"]
    assert meta2.scope == "universal"
    assert meta2.always_include is True


def test_chunk_document_model():
    sample_data = {
        "id": "b1a2c3d4e5f6",
        "text": "sample text",
        "embedding": [0.1, 0.2, 0.3],
        "metadata": {
            "source_file": "test.md",
            "title": "Title",
            "breadcrumb": "Test > Title",
            "category": "website_ban_hang",
            "dimension": "payment_shipping",
        },
    }
    chunk = ChunkDocument.model_validate(sample_data)
    assert chunk.id == "b1a2c3d4e5f6"
    assert chunk.metadata.category == "website_ban_hang"
    assert chunk.metadata.keywords == []


def test_get_universal_chunks_endpoint():
    mock_service = AsyncMock()
    mock_doc = ChunkDocument(
        id="chunk-1",
        text="Universal chunk content",
        metadata=ChunkMetadata(
            source_file="test.md",
            title="A1",
            breadcrumb="Section > A1",
            always_include=True,
            scope="universal",
        ),
    )
    mock_service.get_universal_chunks.return_value = [mock_doc]

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.get("/api/v1/chunks/universal")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "chunk-1"
        assert data[0]["metadata"]["always_include"] is True
    finally:
        app.dependency_overrides.clear()


def test_get_chunk_by_id_endpoint_found():
    mock_service = AsyncMock()
    mock_doc = ChunkDocument(
        id="chunk-1",
        text="Content 1",
        metadata=ChunkMetadata(
            source_file="test.md",
            title="A1",
            breadcrumb="Section > A1",
        ),
    )
    mock_service.get_chunk_by_id.return_value = mock_doc

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.get("/api/v1/chunks/chunk-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chunk-1"
        assert data["text"] == "Content 1"
    finally:
        app.dependency_overrides.clear()


def test_get_chunk_by_id_endpoint_not_found():
    mock_service = AsyncMock()
    mock_service.get_chunk_by_id.return_value = None

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.get("/api/v1/chunks/non-existent-id")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_get_stats_endpoint():
    mock_service = AsyncMock()
    mock_stats = ChunkStatsResponse(
        total_chunks=78,
        universal_count=7,
        by_category={"website_ban_hang": 10},
        by_dimension={"payment_shipping": 5},
        by_source_file={"test.md": 78},
    )
    mock_service.get_stats.return_value = mock_stats

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.get("/api/v1/chunks/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_chunks"] == 78
        assert data["universal_count"] == 7
        assert data["by_category"]["website_ban_hang"] == 10
    finally:
        app.dependency_overrides.clear()


def test_list_chunks_endpoint():
    mock_service = AsyncMock()
    mock_doc = ChunkDocument(
        id="chunk-1",
        text="Content 1",
        metadata=ChunkMetadata(
            source_file="test.md",
            title="A1",
            breadcrumb="Section > A1",
            category="website_ban_hang",
        ),
    )
    mock_service.get_chunks.return_value = (1, [mock_doc])

    app.dependency_overrides[get_chunk_service] = lambda: mock_service
    try:
        response = client.get("/api/v1/chunks?category=website_ban_hang")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["id"] == "chunk-1"
    finally:
        app.dependency_overrides.clear()
