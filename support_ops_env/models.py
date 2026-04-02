from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionType(str, Enum):
    VIEW_QUEUE = "view_queue"
    OPEN_TICKET = "open_ticket"
    SEARCH_KB = "search_kb"
    READ_KB_ARTICLE = "read_kb_article"
    SET_PRIORITY = "set_priority"
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ASSIGN_TEAM = "assign_team"
    DRAFT_REPLY = "draft_reply"
    REQUEST_ESCALATION = "request_escalation"
    ADD_INTERNAL_NOTE = "add_internal_note"
    CLOSE_TICKET = "close_ticket"
    SUBMIT_RESOLUTION = "submit_resolution"


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    subject: str
    body: str
    status: str = "open"
    priority: str = "normal"
    tags: List[str] = Field(default_factory=list)
    assigned_team: Optional[str] = None


class CustomerProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    company_name: str
    plan: str
    invoice_age_days: int = 0
    partial_usage_pct: float = 0.0


class KnowledgeBaseArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_id: str
    title: str
    content: str
    keywords: List[str] = Field(default_factory=list)


class DraftReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = ""


class ActionHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    action_type: ActionType
    payload: Dict[str, Any] = Field(default_factory=dict)


class ExpectedResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_priority: str
    required_tags: Set[str] = Field(default_factory=set)
    required_team: Optional[str] = None
    required_escalation_team: Optional[str] = None
    must_close: bool = False
    required_resolution_code: Optional[str] = None
    required_kb_article_ids: Set[str] = Field(default_factory=set)
    required_reply_phrases: List[str] = Field(default_factory=list)
    forbidden_reply_phrases: List[str] = Field(default_factory=list)
    require_internal_note: bool = False


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    benchmark: str = "support_ops_env"
    difficulty: str
    instructions: str
    max_steps: int
    ticket: Ticket
    customer: CustomerProfile
    kb_articles: List[KnowledgeBaseArticle]
    expected: ExpectedResolution


class SupportOpsAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ActionType
    ticket_id: Optional[str] = None
    query: Optional[str] = None
    article_id: Optional[str] = None
    priority: Optional[str] = None
    tag: Optional[str] = None
    team: Optional[str] = None
    message: Optional[str] = None
    note: Optional[str] = None
    resolution_code: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.strip().lower()


class SupportOpsObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_title: str
    task_instructions: str
    step_count: int
    max_steps: int
    queue_snapshot: List[Dict[str, Any]]
    active_ticket: Optional[Dict[str, Any]]
    visible_kb_results: List[Dict[str, Any]]
    current_draft_reply: str
    current_labels: List[str]
    current_priority: str
    assigned_team: Optional[str]
    escalation_status: Optional[str]
    last_action_status: str
    last_action_error: Optional[str]
    progress_signals: Dict[str, bool]
    available_actions: List[str]


class SupportOpsReward(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float = Field(ge=-1.0, le=1.0)
    components: Dict[str, float] = Field(default_factory=dict)


class SupportOpsState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str
    task_id: str
    step_count: int
    done: bool
    max_steps: int
    ticket_ground_truth: Dict[str, Any]
    expected_resolution: Dict[str, Any]
    action_history: List[ActionHistoryEntry] = Field(default_factory=list)
    reward_breakdown: Dict[str, float] = Field(default_factory=dict)
    mistakes: List[str] = Field(default_factory=list)
    grader_inputs: Dict[str, Any] = Field(default_factory=dict)
    queue: List[Ticket] = Field(default_factory=list)
    active_ticket: Optional[Ticket] = None
    customer: Optional[CustomerProfile] = None
    kb_articles: List[KnowledgeBaseArticle] = Field(default_factory=list)
    kb_results: List[KnowledgeBaseArticle] = Field(default_factory=list)
    draft_reply: DraftReply = Field(default_factory=DraftReply)
    escalation_status: Optional[str] = None
    internal_notes: List[str] = Field(default_factory=list)
    submitted_resolution_code: Optional[str] = None
    visited_articles: Set[str] = Field(default_factory=set)
    achieved_milestones: Set[str] = Field(default_factory=set)
    last_action_status: str = "ok"
    last_action_error: Optional[str] = None
    score: float = 0.0


class StepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: SupportOpsObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)
