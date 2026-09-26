from __future__ import annotations

import logging
import re
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.brief import (
    BriefGenerateRequest,
    BriefGenerateResponse,
    BudgetItem,
    DiscoveryQuestion,
    DiscoveryRequest,
    DiscoveryResponse,
    ProjectEstimation,
    ProjectPhase,
    QuestionOption,
)
from app.services.chunk_service import ChunkService
from app.services.llm_service import LLMService

logger = logging.getLogger("sam_ai.brief")

# 4 Categories with FULL discovery profiles in KB
FULL_CATEGORIES: dict[str, str] = {
    "website_ban_hang": "Website bán hàng (E-commerce)",
    "app_dat_lich": "App đặt lịch / Booking (Spa, Phòng khám, Salon)",
    "crm": "CRM quản lý khách hàng",
    "app_giao_hang": "App đặt hàng / giao hàng (Food & Retail Delivery)",
}

# 10 Categories with PRD references in KB
PARTIAL_CATEGORIES: dict[str, str] = {
    "ai_assistant": "Trợ lý ảo & Chatbot AI",
    "app_giao_duc": "Ứng dụng Giáo dục & LMS",
    "marketing_tool": "Công cụ Marketing & Automation",
    "app_tai_chinh": "Ứng dụng Tài chính & Ví điểm thưởng",
    "erp_noi_bo": "ERP nội bộ doanh nghiệp",
    "hr_nhan_su": "Quản lý nhân sự (HRM)",
    "quan_ly_kho": "Quản lý kho & Xuất nhập tồn",
    "bi_dashboard": "Dashboard & Báo cáo BI",
    "workflow_automation": "Tự động hóa quy trình (Workflow)",
    "event_booking": "Đặt vé sự kiện & Event",
}

ALL_CATEGORIES: dict[str, str] = {**FULL_CATEGORIES, **PARTIAL_CATEGORIES}

# Rule-based routing triggers
CATEGORY_TRIGGERS: dict[str, list[str]] = {
    "app_giao_hang": [
        "đồ ăn",
        "giao hàng",
        "đặt món",
        "ship đồ ăn",
        "food",
        "nhà hàng",
        "quán ăn",
        "trà sữa",
        "retail delivery",
    ],
    "website_ban_hang": [
        "web bán hàng",
        "shop online",
        "bán hàng",
        "thương mại điện tử",
        "e-commerce",
        "bán quần áo",
        "bán mỹ phẩm",
        "bán giày",
    ],
    "app_dat_lich": [
        "đặt lịch",
        "booking",
        "spa",
        "salon",
        "phòng khám",
        "nha khoa",
        "làm đẹp",
        "cắt tóc",
        "đặt bàn",
    ],
    "crm": [
        "crm",
        "quản lý khách hàng",
        "chăm sóc khách hàng",
        "telesale",
        "lead",
    ],
    "app_giao_duc": [
        "học trực tuyến",
        "lms",
        "khóa học",
        "thi trắc nghiệm",
        "luyện thi",
        "giáo dục",
        "e-learning",
    ],
    "ai_assistant": [
        "ai",
        "chatbot",
        "trợ lý ảo",
        "gợi ý sản phẩm",
        "recommendation",
    ],
    "quan_ly_kho": [
        "quản lý kho",
        "kho hàng",
        "xuất nhập tồn",
        "inventory",
    ],
    "hr_nhan_su": [
        "nhân sự",
        "chấm công",
        "tính lương",
        "hrm",
    ],
    "erp_noi_bo": [
        "erp",
        "quản lý nội bộ",
        "doanh nghiệp vừa và nhỏ",
    ],
    "bi_dashboard": [
        "dashboard",
        "báo cáo kinh doanh",
        "bi",
        "bi dashboard",
    ],
    "event_booking": [
        "bán vé",
        "sự kiện",
        "event",
        "ticket",
    ],
    "marketing_tool": [
        "landing page",
        "email marketing",
        "automation marketing",
    ],
    "app_tai_chinh": [
        "ví điểm thưởng",
        "loyalty",
        "quản lý chi tiêu",
        "hóa đơn",
    ],
    "workflow_automation": [
        "quy trình nội bộ",
        "tự động hóa",
        "workflow",
    ],
}


class BriefService:
    """Service orchestrating discovery questions and comprehensive project briefs."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        chunk_service: ChunkService | None = None,
        llm_service: LLMService | None = None,
    ):
        self.db = db
        self.chunk_service = chunk_service or ChunkService(db)
        self.llm_service = llm_service or LLMService()

    async def route_category(
        self, idea: str, preferred_category: str | None = None
    ) -> tuple[str, str, float]:
        """Determine category slug, human display name, and confidence score."""
        if preferred_category and preferred_category in ALL_CATEGORIES:
            return (
                preferred_category,
                ALL_CATEGORIES[preferred_category],
                1.0,
            )

        cleaned_idea = idea.lower()

        # 1. Rule-based trigger matching
        for cat, triggers in CATEGORY_TRIGGERS.items():
            if any(t in cleaned_idea for t in triggers):
                return cat, ALL_CATEGORIES.get(cat, cat), 0.95

        # 2. Semantic search fallback across chunks
        try:
            results = await self.chunk_service.semantic_search(query_text=idea, limit=3)
            for res in results:
                cat = res.get("metadata", {}).get("category")
                if cat and cat in ALL_CATEGORIES:
                    return cat, ALL_CATEGORIES[cat], 0.85
        except Exception as exc:
            logger.warning("Semantic routing fallback failed: %s", exc)

        # Default fallback to website_ban_hang
        return "website_ban_hang", ALL_CATEGORIES["website_ban_hang"], 0.60

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Analyze project idea and return structured discovery questions."""
        session_id = str(uuid.uuid4())
        category, display_name, confidence = await self.route_category(
            request.idea, request.preferred_category
        )

        if category in FULL_CATEGORIES:
            questions = await self._get_questions_from_kb(category)
            source = "kb_lookup"
        else:
            questions = await self._generate_questions_with_llm(
                request.idea, category, display_name
            )
            source = "llm_generated"

        return DiscoveryResponse(
            session_id=session_id,
            detected_category=category,
            category_display_name=display_name,
            confidence=confidence,
            source=source,
            questions=questions,
        )

    async def _get_questions_from_kb(self, category: str) -> list[DiscoveryQuestion]:
        """Fetch and parse Q&A chunks stored in MongoDB for FULL categories."""
        cursor = (
            self.db["chunks"]
            .find(
                {
                    "metadata.category": category,
                    "metadata.title": {"$regex": "Nhóm câu hỏi"},
                }
            )
            .sort("metadata.title", 1)
        )

        raw_chunks = [doc async for doc in cursor]

        # In-memory parsing
        parsed_questions: list[DiscoveryQuestion] = []
        global_idx = 1

        for doc in raw_chunks:
            title = doc.get("metadata", {}).get("title", "Khảo sát")
            group_match = re.search(r"Nhóm câu hỏi \d+\s*[—–-]\s*(.*)", title)
            group_name = group_match.group(1).strip() if group_match else title

            extracted = self._parse_chunk_questions(
                doc.get("text", ""), group_name, start_idx=global_idx
            )
            # Pick the top 1-2 most essential questions per group for high-quality UX
            parsed_questions.extend(extracted[:2])
            global_idx += len(extracted)

        return parsed_questions

    @staticmethod
    def _parse_chunk_questions(
        text: str, group_name: str, start_idx: int = 1
    ) -> list[DiscoveryQuestion]:
        """Extract structured questions and options from Markdown tables or bullet lists."""
        questions: list[DiscoveryQuestion] = []
        lines = text.strip().split("\n")
        idx = start_idx

        for line in lines:
            line_str = line.strip()
            if (
                not line_str
                or line_str.startswith("[Nguồn:")
                or line_str.startswith("**")
                or "---" in line_str
            ):
                continue

            # Format 1: Markdown Table (| Câu hỏi | Lựa chọn gợi ý |)
            if line_str.startswith("|") and line_str.endswith("|"):
                parts = [p.strip() for p in line_str.strip("|").split("|")]
                if (
                    len(parts) >= 2
                    and parts[0] != "Câu hỏi"
                    and not parts[0].startswith("---")
                ):
                    q_text = parts[0]
                    raw_opts = parts[1].split("/")
                    opts = [
                        QuestionOption(
                            label=o.strip(),
                            value=re.sub(r"[^\w\s-]", "", o.strip())
                            .lower()
                            .replace(" ", "_"),
                        )
                        for o in raw_opts
                        if o.strip()
                    ]
                    q_type = (
                        "multiple_choice"
                        if any(
                            w in q_text.lower()
                            for w in ["nào", "những", "các", "phương thức"]
                        )
                        else "single_choice"
                    )
                    questions.append(
                        DiscoveryQuestion(
                            id=f"q_{idx}",
                            group=group_name,
                            question=q_text,
                            type=q_type,
                            options=opts,
                            allow_custom=True,
                        )
                    )
                    idx += 1
                continue

            # Format 2: Bullet points with parentheses: - Câu hỏi? (Option 1 / Option 2)
            if line_str.startswith("-"):
                content = line_str.lstrip("-").strip()
                m = re.search(r"^(.*?)\s*\((.*?)\)\s*\??$", content)
                if m:
                    q_text = m.group(1).strip()
                    if not q_text.endswith("?"):
                        q_text += "?"
                    raw_opts = m.group(2).split("/")
                    opts = [
                        QuestionOption(
                            label=o.strip(),
                            value=re.sub(r"[^\w\s-]", "", o.strip())
                            .lower()
                            .replace(" ", "_"),
                        )
                        for o in raw_opts
                        if o.strip()
                    ]
                    q_type = (
                        "multiple_choice"
                        if any(w in q_text.lower() for w in ["nào", "những", "các"])
                        else "single_choice"
                    )
                    questions.append(
                        DiscoveryQuestion(
                            id=f"q_{idx}",
                            group=group_name,
                            question=q_text,
                            type=q_type,
                            options=opts,
                            allow_custom=True,
                        )
                    )
                    idx += 1
                    continue

                # Format 3: Field: Option 1 / Option 2
                if ":" in content:
                    parts = content.split(":", 1)
                    q_text = parts[0].strip()
                    if not q_text.endswith("?"):
                        q_text += "?"
                    raw_opts = parts[1].split("/")
                    opts = [
                        QuestionOption(
                            label=o.strip(),
                            value=re.sub(r"[^\w\s-]", "", o.strip())
                            .lower()
                            .replace(" ", "_"),
                        )
                        for o in raw_opts
                        if o.strip()
                    ]
                    questions.append(
                        DiscoveryQuestion(
                            id=f"q_{idx}",
                            group=group_name,
                            question=q_text,
                            type="single_choice",
                            options=opts,
                            allow_custom=True,
                        )
                    )
                    idx += 1

        return questions

    async def _generate_questions_with_llm(
        self, idea: str, category: str, display_name: str
    ) -> list[DiscoveryQuestion]:
        """Generate structured discovery questions using LLM for partial categories."""
        # Retrieve PRD chunks as domain context
        cursor = self.db["chunks"].find({"metadata.category": category}).limit(2)
        prd_chunks = [doc.get("text", "") async for doc in cursor]
        context_text = "\n\n".join(prd_chunks)

        system_prompt = (
            "Bạn là chuyên gia phân tích nghiệp vụ phần mềm (Senior IT Business Analyst).\n"
            f"Hãy tạo ra 5 câu hỏi khảo sát trắc nghiệm ngắn gọn, thực tế để khách hàng làm rõ ý tưởng '{display_name}'.\n"
            "Mỗi câu hỏi phải bao gồm các lựa chọn (options) thực tế có thể chọn ngay.\n\n"
            "QUY TẮC ĐỊNH DẠNG (BẮT BUỘC):\n"
            "- Tuyệt đối KHÔNG dùng bất kỳ emoji, icon, sticker hoặc ký tự trang trí đặc biệt nào trong câu hỏi và lựa chọn.\n"
            "- Giữ câu từ ngắn gọn, trang trọng, tự nhiên và chuyên nghiệp.\n\n"
            "Định dạng đầu ra BẮT BUỘC là JSON theo cấu trúc:\n"
            "{\n"
            '  "questions": [\n'
            '    {"id": "q_1", "group": "Mục tiêu và Người dùng", "question": "...", "type": "single_choice", "options": [{"label": "...", "value": "..."}, ...], "allow_custom": true},\n'
            '    {"id": "q_2", "group": "Tính năng cốt lõi", "question": "...", "type": "multiple_choice", "options": [{"label": "...", "value": "..."}, ...], "allow_custom": true},\n'
            '    {"id": "q_3", "group": "Nền tảng và Thiết bị", "question": "...", "type": "single_choice", "options": [{"label": "...", "value": "..."}, ...], "allow_custom": false},\n'
            '    {"id": "q_4", "group": "Tích hợp và Dữ liệu", "question": "...", "type": "multiple_choice", "options": [{"label": "...", "value": "..."}, ...], "allow_custom": true},\n'
            '    {"id": "q_5", "group": "Tiến độ và Ngân sách", "question": "...", "type": "single_choice", "options": [{"label": "...", "value": "..."}, ...], "allow_custom": true}\n'
            "  ]\n"
            "}"
        )

        user_message = f"Ý tưởng của khách: {idea}\n\nTài liệu tham khảo chuyên môn:\n{context_text}"

        try:
            data = await self.llm_service.chat_json(system_prompt, user_message)
            raw_questions = data.get("questions", [])
            questions: list[DiscoveryQuestion] = []
            for item in raw_questions:
                opts = [
                    QuestionOption(
                        label=o.get("label", ""),
                        value=o.get("value", o.get("label", ""))
                        .lower()
                        .replace(" ", "_"),
                    )
                    for o in item.get("options", [])
                ]
                questions.append(
                    DiscoveryQuestion(
                        id=item.get("id", f"q_{len(questions) + 1}"),
                        group=item.get("group", "Khảo sát"),
                        question=item.get("question", ""),
                        type=item.get("type", "single_choice"),
                        options=opts,
                        allow_custom=item.get("allow_custom", True),
                    )
                )
            if questions:
                return questions
        except Exception as exc:
            logger.warning("LLM question generation failed, using fallback: %s", exc)

        # Fallback template if LLM is offline or fails
        return [
            DiscoveryQuestion(
                id="q_1",
                group="Mục tiêu & Người dùng",
                question="Đối tượng người dùng chính của hệ thống là ai?",
                type="single_choice",
                options=[
                    QuestionOption(label="Khách hàng đại chúng (B2C)", value="b2c"),
                    QuestionOption(label="Doanh nghiệp đối tác (B2B)", value="b2b"),
                    QuestionOption(label="Nội bộ nhân viên", value="internal"),
                ],
            ),
            DiscoveryQuestion(
                id="q_2",
                group="Tính năng cốt lõi",
                question="Các tính năng quan trọng nhất cần ưu tiên cho bản MVP?",
                type="multiple_choice",
                options=[
                    QuestionOption(
                        label="Quản lý dữ liệu & Báo cáo", value="crud_reports"
                    ),
                    QuestionOption(
                        label="Phân quyền tài khoản nhiều cấp", value="roles"
                    ),
                    QuestionOption(label="Tự động hóa luồng xử lý", value="automation"),
                ],
            ),
            DiscoveryQuestion(
                id="q_3",
                group="Nền tảng triển khai",
                question="Nền tảng mong muốn khởi chạy ban đầu?",
                type="single_choice",
                options=[
                    QuestionOption(label="Website Responsive", value="web"),
                    QuestionOption(label="Mobile App (iOS & Android)", value="mobile"),
                    QuestionOption(label="Cả Web và Mobile App", value="both"),
                ],
            ),
            DiscoveryQuestion(
                id="q_4",
                group="Ngân sách & Thời gian",
                question="Ngân sách dự kiến của bạn cho dự án này?",
                type="single_choice",
                options=[
                    QuestionOption(label="Dưới 30 triệu", value="under_30m"),
                    QuestionOption(label="30 - 70 triệu", value="30_70m"),
                    QuestionOption(label="Trên 70 triệu", value="above_70m"),
                ],
            ),
        ]

    async def generate(self, request: BriefGenerateRequest) -> BriefGenerateResponse:
        """Compile user answers and knowledge chunks into professional brief and estimation."""
        # 1. Retrieve knowledge context chunks from DB
        category = request.category
        context_chunks: list[str] = []

        # Category attribute dimensions & brief template
        cat_cursor = self.db["chunks"].find({"metadata.category": category}).limit(5)
        async for doc in cat_cursor:
            context_chunks.append(
                f"[{doc.get('metadata', {}).get('title')}]:\n{doc.get('text')}"
            )

        # Universal chunks (A1, A6)
        uni_cursor = self.db["chunks"].find({"metadata.scope": "universal"}).limit(3)
        async for doc in uni_cursor:
            context_chunks.append(
                f"[{doc.get('metadata', {}).get('title')}]:\n{doc.get('text')}"
            )

        joined_context = "\n\n---\n\n".join(context_chunks)

        # 2. Format user answers
        answers_text = ""
        for ans in request.answers:
            selected_str = (
                ", ".join(ans.selected_options)
                if ans.selected_options
                else "Không chọn"
            )
            if ans.custom_input:
                selected_str += f" (Khác: {ans.custom_input})"
            answers_text += f"- **{ans.question}**: {selected_str}\n"

        # 3. LLM synthesis
        system_prompt = (
            "Bạn là Chuyên gia Cao cấp về Giải pháp Phần mềm & Giám đốc Dự án (Senior Software Architect & PM).\n"
            "Nhiệm vụ của bạn là tổng hợp toàn bộ câu trả lời của khách hàng cùng tài liệu kỹ thuật chuẩn thành một Bản Brief Dự Án hoàn chỉnh, chuyên nghiệp và bảng ước lượng thời gian & ngân sách chính xác.\n\n"
            "QUY TẮC ĐỊNH DẠNG VĂN BẢN (BẮT BUỘC):\n"
            "- Tuyệt đối KHÔNG sử dụng bất kỳ emoji, icon, sticker hoặc ký tự trang trí đồ họa nào (ví dụ: 🚀, ⚡, 🎯, 💡, 📋, 🤖, ⭐, v.v.).\n"
            "- Cấu trúc bản brief và toàn bộ nội dung chỉ được phân tầng theo tiêu đề Markdown (#, ##, ###) và danh sách gạch đầu dòng (-) hoặc thụt lề (  -) cho các mục con.\n"
            "- Tuyệt đối không dùng phong cách viết quá đậm màu AI (như các lời chúc, câu mở đầu sáo rỗng, các ký hiệu màu mè).\n"
            "- Văn phong kỹ thuật, chuẩn chỉ, ngắn gọn, mạch lạc của tài liệu đặc tả phần mềm chuyên nghiệp.\n\n"
            "Định dạng phản hồi BẮT BUỘC là JSON theo cấu trúc sau:\n"
            "{\n"
            '  "project_title": "Tên dự án chuyên nghiệp",\n'
            '  "summary": "Tóm tắt dự án 2-3 câu ngắn gọn, súc tích",\n'
            '  "target_audience": "Mô tả đối tượng người dùng cuối và quản trị viên",\n'
            '  "core_features": ["Tính năng 1", "Tính năng 2", ...],\n'
            '  "integrations": ["Tích hợp 1", ...],\n'
            '  "design_direction": "Mô tả phong cách giao diện và màu sắc",\n'
            '  "upsell_suggestions": ["Gợi ý nâng cấp giai đoạn 2..."],\n'
            '  "estimation": {\n'
            '    "timeline_range": "e.g. 4 – 6 tuần",\n'
            '    "mvp_timeline": "e.g. 3 tuần",\n'
            '    "phases": [\n'
            '      {"phase_name": "Giai đoạn 1: Thiết kế UI/UX", "duration": "1 tuần", "deliverables": "Figma Wireframe và Prototype"},\n'
            '      {"phase_name": "Giai đoạn 2: Lập trình Backend và Core App", "duration": "2 – 3 tuần", "deliverables": "API, Database, Module cốt lõi"},\n'
            '      {"phase_name": "Giai đoạn 3: Tích hợp, Testing và Triển khai", "duration": "1 – 2 tuần", "deliverables": "UAT, Deploy Server"}\n'
            "    ],\n"
            '    "budget_range": "e.g. 25.000.000 – 45.000.000 VNĐ",\n'
            '    "budget_breakdown": [\n'
            '      {"item": "Giao diện UI/UX Frontend", "cost_range": "8.000.000 – 12.000.000 VNĐ"},\n'
            '      {"item": "Hệ thống Quản trị và Backend", "cost_range": "12.000.000 – 20.000.000 VNĐ"},\n'
            '      {"item": "Tích hợp dịch vụ và Triển khai", "cost_range": "5.000.000 – 13.000.000 VNĐ"}\n'
            "    ],\n"
            '    "budget_note": "Ghi chú giải trình ngân sách và giải pháp tiết kiệm chi phí"\n'
            "  },\n"
            '  "raw_brief_markdown": "# BRIEF DỰ ÁN: [TÊN DỰ ÁN]\\n\\n### 1. Mục tiêu dự án\\n- ...\\n\\n### 2. Danh sách tính năng cốt lõi (MVP)\\n- ...\\n\\n### 3. Tích hợp bên thứ ba\\n- ...\\n\\n### 4. Định hướng thiết kế và giao diện\\n- ...\\n\\n### 5. Dự toán thời gian và ngân sách\\n- Thời gian dự kiến: ...\\n- Ngân sách dự kiến: ...\\n- Các giai đoạn triển khai:\\n  - Giai đoạn 1: ...\\n  - Giai đoạn 2: ...\\n- Bóc tách chi phí sơ bộ:\\n  - Hạng mục 1: ...\\n  - Hạng mục 2: ...\\n\\n### 6. Đề xuất nâng cấp giai đoạn sau\\n- ..."\n'
            "}"
        )

        user_message = (
            f"Ý tưởng ban đầu: {request.idea}\n"
            f"Danh mục dự án: {category}\n\n"
            f"Câu trả lời khảo sát từ khách hàng:\n{answers_text}\n\n"
            f"Tài liệu tiêu chuẩn kỹ thuật & ma trận định giá tham chiếu:\n{joined_context}"
        )

        try:
            data = await self.llm_service.chat_json(system_prompt, user_message)
            est = data.get("estimation", {})
            phases = [
                ProjectPhase(
                    phase_name=p.get("phase_name", "Giai đoạn"),
                    duration=p.get("duration", "1-2 tuần"),
                    deliverables=p.get("deliverables", "Deliverables"),
                )
                for p in est.get("phases", [])
            ]
            breakdown = [
                BudgetItem(
                    item=b.get("item", "Hạng mục"),
                    cost_range=b.get("cost_range", "Đang cập nhật"),
                )
                for b in est.get("budget_breakdown", [])
            ]

            estimation = ProjectEstimation(
                timeline_range=est.get("timeline_range", "3 – 5 tuần"),
                mvp_timeline=est.get("mvp_timeline", "3 tuần"),
                phases=phases,
                budget_range=est.get("budget_range", "25.000.000 – 40.000.000 VNĐ"),
                budget_breakdown=breakdown,
                budget_note=est.get(
                    "budget_note", "Dự toán sơ bộ theo phạm vi yêu cầu."
                ),
            )

            return BriefGenerateResponse(
                session_id=request.session_id,
                project_title=data.get("project_title", f"Dự án {request.idea}"),
                summary=data.get("summary", "Bản mô tả dự án chuyên nghiệp"),
                target_audience=data.get("target_audience", "Người dùng cuối"),
                core_features=data.get("core_features", []),
                integrations=data.get("integrations", []),
                design_direction=data.get(
                    "design_direction", "Hiện đại, thân thiện người dùng"
                ),
                upsell_suggestions=data.get("upsell_suggestions", []),
                estimation=estimation,
                raw_brief_markdown=data.get(
                    "raw_brief_markdown", f"# BRIEF DỰ ÁN: {request.idea}"
                ),
            )
        except Exception as exc:
            logger.warning(
                "LLM brief synthesis failed, using rule-based synthesis fallback: %s",
                exc,
            )
            return self._fallback_brief_generate(request)

    def _fallback_brief_generate(
        self, request: BriefGenerateRequest
    ) -> BriefGenerateResponse:
        """Deterministic fallback synthesis if LLM is offline or model call fails."""
        display_name = ALL_CATEGORIES.get(request.category, request.category)
        features: list[str] = []
        integrations: list[str] = []

        for ans in request.answers:
            if "tính năng" in ans.question.lower() or "menu" in ans.question.lower():
                features.extend(ans.selected_options)
            elif (
                "tích hợp" in ans.question.lower()
                or "thanh toán" in ans.question.lower()
            ):
                integrations.extend(ans.selected_options)

        if not features:
            features = [
                "Đăng ký & Đăng nhập",
                "Giao diện danh mục chính",
                "Trang quản trị Admin",
            ]
        if not integrations:
            integrations = ["Cổng thanh toán trực tuyến", "Dịch vụ thông báo Email/SMS"]

        estimation = ProjectEstimation(
            timeline_range="3 – 5 tuần",
            mvp_timeline="3 tuần",
            phases=[
                ProjectPhase(
                    phase_name="Giai đoạn 1: UI/UX & Luồng người dùng",
                    duration="1 tuần",
                    deliverables="Figma Wireframe & Prototype",
                ),
                ProjectPhase(
                    phase_name="Giai đoạn 2: Lập trình Core Features & Admin",
                    duration="2 – 3 tuần",
                    deliverables="Frontend, Backend API, Database",
                ),
                ProjectPhase(
                    phase_name="Giai đoạn 3: Kiểm thử, Tích hợp & Triển khai",
                    duration="1 tuần",
                    deliverables="UAT, Deploy Cloud Server",
                ),
            ],
            budget_range="25.000.000 – 45.000.000 VNĐ",
            budget_breakdown=[
                BudgetItem(
                    item="Giao diện Web & Mobile Responsive",
                    cost_range="10.000.000 – 15.000.000 VNĐ",
                ),
                BudgetItem(
                    item="Backend API & Quản trị Admin",
                    cost_range="12.000.000 – 20.000.000 VNĐ",
                ),
                BudgetItem(
                    item="Tích hợp dịch vụ & Kiểm thử",
                    cost_range="5.000.000 – 10.000.000 VNĐ",
                ),
            ],
            budget_note="Chi phí ước tính dựa trên phạm vi MVP cơ bản.",
        )

        phases_text = "\n".join(
            f"  - {p.phase_name}: {p.duration} ({p.deliverables})"
            for p in estimation.phases
        )
        breakdown_text = "\n".join(
            f"  - {b.item}: {b.cost_range}" for b in estimation.budget_breakdown
        )

        markdown = (
            f"# BRIEF DỰ ÁN: {request.idea.upper()}\n\n"
            f"Danh mục: {display_name}\n\n"
            f"### 1. Mục tiêu dự án\n"
            f"- Xây dựng hệ thống giải quyết bài toán: {request.idea}\n"
            f"- Đối tượng phục vụ: Khách hàng người dùng cuối và đội ngũ quản trị\n\n"
            f"### 2. Danh sách tính năng cốt lõi (MVP)\n"
            + "\n".join(f"- {f}" for f in features)
            + "\n\n### 3. Tích hợp bên thứ ba\n"
            + "\n".join(f"- {i}" for i in integrations)
            + "\n\n### 4. Định hướng thiết kế và giao diện\n"
            "- Giao diện tối ưu trải nghiệm trên thiết bị di động\n"
            "- Luồng thao tác tinh gọn, rõ ràng, tốc độ tải nhanh\n\n"
            f"### 5. Dự toán thời gian và ngân sách\n"
            f"- Thời gian dự kiến: {estimation.timeline_range} (Giai đoạn MVP: {estimation.mvp_timeline})\n"
            f"- Ngân sách dự kiến: {estimation.budget_range}\n"
            f"- Các giai đoạn triển khai:\n{phases_text}\n"
            f"- Bóc tách chi phí sơ bộ:\n{breakdown_text}\n\n"
            "### 6. Đề xuất nâng cấp giai đoạn sau\n"
            "- Ứng dụng di động chuyên biệt (Native App)\n"
            "- Tự động hóa quy trình chăm sóc khách hàng và tiếp thị đa kênh\n"
        )

        return BriefGenerateResponse(
            session_id=request.session_id,
            project_title=f"Dự án Nền tảng {display_name}",
            summary=f"Dự án phát triển giải pháp {display_name} đáp ứng yêu cầu: {request.idea}.",
            target_audience="Khách hàng người dùng cuối và quản trị viên hệ thống",
            core_features=features,
            integrations=integrations,
            design_direction="Giao diện hiện đại, tối ưu trải nghiệm người dùng di động",
            upsell_suggestions=[
                "Ứng dụng di động Native",
                "Tích hợp Chatbot AI chăm sóc 24/7",
            ],
            estimation=estimation,
            raw_brief_markdown=markdown,
        )
