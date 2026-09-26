from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    """Option item for a discovery question."""

    label: str = Field(..., description="Display label for the user")
    value: str = Field(..., description="Normalized value or slug")


class DiscoveryQuestion(BaseModel):
    """Structured question for the interactive discovery phase."""

    id: str = Field(..., description="Unique question identifier")
    group: str = Field(..., description="Question group or dimension name")
    question: str = Field(..., description="Question title")
    type: str = Field(
        default="single_choice",
        description="Question input type: 'single_choice' | 'multiple_choice' | 'text'",
    )
    options: list[QuestionOption] = Field(
        default_factory=list, description="List of pre-configured options"
    )
    allow_custom: bool = Field(
        default=True, description="Allow user to type a custom answer"
    )


class DiscoveryRequest(BaseModel):
    """Request payload to initiate project discovery."""

    idea: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Initial rough project idea from customer",
        examples=["web bán đồ ăn", "app đặt lịch spa"],
    )
    preferred_category: str | None = Field(
        default=None,
        description="Explicit category if already known or chosen",
        examples=["app_giao_hang", "website_ban_hang"],
    )


class DiscoveryResponse(BaseModel):
    """Response containing category routing and discovery questions."""

    session_id: str = Field(..., description="UUID session identifier")
    detected_category: str = Field(..., description="Detected category slug")
    category_display_name: str = Field(..., description="Human-readable category name")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Routing confidence score"
    )
    source: str = Field(
        ..., description="Source of questions: 'kb_lookup' or 'llm_generated'"
    )
    questions: list[DiscoveryQuestion] = Field(
        ..., description="List of structured discovery questions"
    )


class QuestionAnswer(BaseModel):
    """Answer provided by user for a discovery question."""

    question_id: str = Field(..., description="ID matching DiscoveryQuestion.id")
    question: str = Field(..., description="The question text")
    selected_options: list[str] = Field(
        default_factory=list, description="List of selected option labels"
    )
    custom_input: str | None = Field(
        default=None, description="Free-text custom answer if any"
    )


class BriefGenerateRequest(BaseModel):
    """Request payload to compile final brief and estimations."""

    session_id: str = Field(..., description="Session ID from discovery step")
    idea: str = Field(..., description="Original user idea")
    category: str = Field(..., description="Target category slug")
    answers: list[QuestionAnswer] = Field(
        ..., min_length=1, description="List of answered questions"
    )


class ProjectPhase(BaseModel):
    """Timeline phase in project estimation."""

    phase_name: str = Field(..., description="Name of the development phase")
    duration: str = Field(..., description="Duration string, e.g., '1-2 tuần'")
    deliverables: str = Field(..., description="Key deliverables for this phase")


class BudgetItem(BaseModel):
    """Budget breakdown line item."""

    item: str = Field(..., description="Scope or module name")
    cost_range: str = Field(
        ..., description="Estimated cost range, e.g., '8.000.000 - 12.000.000 VNĐ'"
    )


class ProjectEstimation(BaseModel):
    """Estimation for project duration and financial budget."""

    timeline_range: str = Field(..., description="Overall timeline, e.g., '4 - 6 tuần'")
    mvp_timeline: str = Field(
        ..., description="Fastest timeline for MVP, e.g., '3 tuần'"
    )
    phases: list[ProjectPhase] = Field(
        default_factory=list, description="Phased timeline breakdown"
    )
    budget_range: str = Field(
        ..., description="Overall budget range, e.g., '25.000.000 - 45.000.000 VNĐ'"
    )
    budget_breakdown: list[BudgetItem] = Field(
        default_factory=list, description="Module cost breakdown"
    )
    budget_note: str = Field(default="", description="Assumptions or cost saving notes")


class BriefGenerateResponse(BaseModel):
    """Final generated project brief and estimations."""

    session_id: str = Field(..., description="Session ID")
    project_title: str = Field(..., description="Professional project title")
    summary: str = Field(..., description="2-3 sentence project overview")
    target_audience: str = Field(..., description="Target end users and operators")
    core_features: list[str] = Field(
        ..., description="Key core functional requirements (MVP)"
    )
    integrations: list[str] = Field(
        default_factory=list, description="Third-party systems or APIs"
    )
    design_direction: str = Field(
        ..., description="UI/UX style and aesthetic direction"
    )
    upsell_suggestions: list[str] = Field(
        default_factory=list, description="Recommended phase 2 upgrades"
    )
    estimation: ProjectEstimation = Field(
        ..., description="Timeline and budget projections"
    )
    raw_brief_markdown: str = Field(
        ..., description="Complete brief document in formatted Markdown"
    )
