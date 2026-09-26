from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.brief import get_brief_service
from app.main import app
from app.schemas.brief import (
    BriefGenerateRequest,
    BriefGenerateResponse,
    BudgetItem,
    DiscoveryQuestion,
    DiscoveryRequest,
    DiscoveryResponse,
    ProjectEstimation,
    ProjectPhase,
    QuestionAnswer,
    QuestionOption,
)
from app.services.brief_service import BriefService
from app.services.llm_service import LLMService

client = TestClient(app)


def test_brief_schemas_validation():
    # 1. DiscoveryRequest
    req = DiscoveryRequest(idea="web bán đồ ăn nhanh")
    assert req.idea == "web bán đồ ăn nhanh"
    assert req.preferred_category is None

    # 2. DiscoveryQuestion & Option
    opt = QuestionOption(label="Tự ship", value="self_ship")
    q = DiscoveryQuestion(
        id="q_1",
        group="Vận hành",
        question="Ai giao hàng?",
        type="single_choice",
        options=[opt],
    )
    assert q.id == "q_1"
    assert len(q.options) == 1

    # 3. DiscoveryResponse
    res = DiscoveryResponse(
        session_id="1234-uuid",
        detected_category="app_giao_hang",
        category_display_name="App giao hàng",
        confidence=0.95,
        source="kb_lookup",
        questions=[q],
    )
    assert res.detected_category == "app_giao_hang"

    # 4. BriefGenerateRequest
    ans = QuestionAnswer(
        question_id="q_1",
        question="Ai giao hàng?",
        selected_options=["Tự ship"],
    )
    gen_req = BriefGenerateRequest(
        session_id="1234-uuid",
        idea="web bán đồ ăn",
        category="app_giao_hang",
        answers=[ans],
    )
    assert len(gen_req.answers) == 1


def test_parse_chunk_questions():
    # Test table format
    table_text = (
        "[Nguồn: test.md]\n"
        "| Câu hỏi | Lựa chọn gợi ý |\n"
        "|---|---|\n"
        "| Bạn bán mặt hàng gì? | Thời trang / Đồ ăn / Mỹ phẩm |\n"
        "| Quy mô sản phẩm? | Nhỏ / Vừa / Lớn |\n"
    )
    questions = BriefService._parse_chunk_questions(table_text, "Mục tiêu")
    assert len(questions) == 2
    assert questions[0].question == "Bạn bán mặt hàng gì?"
    assert len(questions[0].options) == 3
    assert questions[0].options[0].label == "Thời trang"

    # Test bullet point format
    bullet_text = (
        "- Hình thức giao hàng? (Tự ship / AhaMove / GrabExpress)\n"
        "- Ngân sách: Dưới 30tr / 30-60tr / Trên 60tr\n"
    )
    q_bullets = BriefService._parse_chunk_questions(bullet_text, "Vận hành")
    assert len(q_bullets) == 2
    assert "Hình thức giao hàng" in q_bullets[0].question
    assert len(q_bullets[0].options) == 3
    assert q_bullets[1].options[0].label == "Dưới 30tr"


@pytest.mark.asyncio
async def test_route_category_logic():
    mock_db = MagicMock()
    mock_chunk_service = AsyncMock()
    service = BriefService(db=mock_db, chunk_service=mock_chunk_service)

    # Trigger rule for food delivery
    cat, name, conf = await service.route_category("cần làm web bán đồ ăn nhanh")
    assert cat == "app_giao_hang"
    assert conf >= 0.9

    # Trigger rule for e-commerce
    cat, name, conf = await service.route_category("xây dựng shop online bán quần áo")
    assert cat == "website_ban_hang"
    assert conf >= 0.9

    # Trigger rule for booking
    cat, name, conf = await service.route_category("hệ thống đặt lịch spa làm đẹp")
    assert cat == "app_dat_lich"
    assert conf >= 0.9

    # Preferred category override
    cat, name, conf = await service.route_category(
        "nền tảng chung", preferred_category="crm"
    )
    assert cat == "crm"
    assert conf == 1.0


@pytest.mark.asyncio
async def test_llm_service_mocked():
    llm = LLMService(provider="ollama", model="qwen2.5:3b")

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {
            "message": {
                "role": "assistant",
                "content": '{"summary": "Test brief summary", "title": "Test Title"}',
            }
        }
        mock_post.return_value = mock_resp

        data = await llm.chat_json("System prompt", "User prompt")
        assert data["summary"] == "Test brief summary"
        assert data["title"] == "Test Title"


def test_discovery_endpoint():
    mock_service = AsyncMock()
    mock_service.discover.return_value = DiscoveryResponse(
        session_id="test-session-123",
        detected_category="app_giao_hang",
        category_display_name="App giao hàng / đặt món",
        confidence=0.95,
        source="kb_lookup",
        questions=[
            DiscoveryQuestion(
                id="q_1",
                group="Vận hành",
                question="Hình thức giao đồ ăn của bạn là gì?",
                type="single_choice",
                options=[QuestionOption(label="Tự ship", value="self_ship")],
            )
        ],
    )

    app.dependency_overrides[get_brief_service] = lambda: mock_service
    try:
        response = client.post(
            "/api/v1/brief/discovery",
            json={"idea": "web bán đồ ăn"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["detected_category"] == "app_giao_hang"
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == "q_1"
    finally:
        app.dependency_overrides.clear()


def test_generate_brief_endpoint():
    mock_service = AsyncMock()
    mock_service.generate.return_value = BriefGenerateResponse(
        session_id="test-session-123",
        project_title="Dự án Web Bán & Giao Đồ Ăn",
        summary="Tóm tắt dự án bán đồ ăn",
        target_audience="Khách hàng và chủ quán",
        core_features=["Menu món", "Đặt hàng", "Thanh toán"],
        integrations=["AhaMove", "VietQR"],
        design_direction="Hiện đại, tông cam ấm",
        upsell_suggestions=["App di động"],
        estimation=ProjectEstimation(
            timeline_range="3 - 5 tuần",
            mvp_timeline="3 tuần",
            phases=[
                ProjectPhase(
                    phase_name="Giai đoạn 1",
                    duration="1 tuần",
                    deliverables="UI/UX",
                )
            ],
            budget_range="25.000.000 - 40.000.000 VNĐ",
            budget_breakdown=[
                BudgetItem(
                    item="Frontend & UI",
                    cost_range="10.000.000 - 15.000.000 VNĐ",
                )
            ],
            budget_note="Chi phí cơ bản",
        ),
        raw_brief_markdown="# BRIEF DỰ ÁN",
    )

    app.dependency_overrides[get_brief_service] = lambda: mock_service
    try:
        payload = {
            "session_id": "test-session-123",
            "idea": "web bán đồ ăn",
            "category": "app_giao_hang",
            "answers": [
                {
                    "question_id": "q_1",
                    "question": "Hình thức giao đồ ăn?",
                    "selected_options": ["Tự ship"],
                }
            ],
        }
        response = client.post("/api/v1/brief/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["project_title"] == "Dự án Web Bán & Giao Đồ Ăn"
        assert data["estimation"]["timeline_range"] == "3 - 5 tuần"
        assert data["estimation"]["budget_range"] == "25.000.000 - 40.000.000 VNĐ"
        assert len(data["core_features"]) == 3
    finally:
        app.dependency_overrides.clear()
