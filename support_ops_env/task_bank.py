from support_ops_env.models import (
    CustomerProfile,
    ExpectedResolution,
    KnowledgeBaseArticle,
    TaskSpec,
    Ticket,
)


def build_task_bank() -> dict[str, TaskSpec]:
    t1 = TaskSpec(
        task_id="password_reset_triage",
        title="Password Reset Queue Triage",
        difficulty="easy",
        instructions=(
            "Handle urgent login issue. Check account context, set correct priority, "
            "apply auth tag, consult password reset KB, draft concise reply, and close."
        ),
        max_steps=8,
        ticket=Ticket(
            ticket_id="T-1001",
            subject="Locked out after MFA reset",
            body="I cannot log in after resetting MFA. Please help ASAP.",
            priority="normal",
        ),
        customer=CustomerProfile(
            customer_id="C-ACME",
            company_name="Acme Co",
            plan="enterprise",
        ),
        kb_articles=[
            KnowledgeBaseArticle(
                article_id="KB-RESET-01",
                title="Secure Password Reset Flow",
                content="Use verified reset flow, confirm identity, then rotate sessions.",
                keywords=["password", "reset", "login", "mfa"],
            ),
            KnowledgeBaseArticle(
                article_id="KB-BILL-02",
                title="Invoice Export",
                content="How to export invoice PDFs.",
                keywords=["invoice", "billing", "export"],
            ),
        ],
        expected=ExpectedResolution(
            required_priority="high",
            required_tags={"auth", "login"},
            required_team="support_l1",
            must_close=True,
            required_resolution_code="password_reset_guided",
            required_kb_article_ids={"KB-RESET-01"},
            required_reply_phrases=[
                "verify your identity",
                "password reset",
                "let us know once complete",
            ],
            forbidden_reply_phrases=["share your password"],
        ),
    )

    t2 = TaskSpec(
        task_id="billing_refund_policy",
        title="Billing Refund With Policy Constraints",
        difficulty="medium",
        instructions=(
            "Evaluate refund request with partial usage and invoice age policy. "
            "Route correctly, avoid over-promising, and provide policy-compliant reply."
        ),
        max_steps=10,
        ticket=Ticket(
            ticket_id="T-2201",
            subject="Need a refund for annual upgrade",
            body="We upgraded 35 days ago and used part of the plan. Requesting full refund.",
            priority="normal",
        ),
        customer=CustomerProfile(
            customer_id="C-BETA",
            company_name="Beta Labs",
            plan="pro_annual",
            invoice_age_days=35,
            partial_usage_pct=0.48,
        ),
        kb_articles=[
            KnowledgeBaseArticle(
                article_id="KB-REFUND-01",
                title="Refund Policy v3",
                content="After 30 days only prorated credits are eligible when usage exists.",
                keywords=["refund", "billing", "prorated", "policy"],
            ),
            KnowledgeBaseArticle(
                article_id="KB-SEC-01",
                title="Suspicious Login Escalation",
                content="Security escalation runbook.",
                keywords=["security", "suspicious", "login"],
            ),
        ],
        expected=ExpectedResolution(
            required_priority="normal",
            required_tags={"billing", "refund"},
            required_team="billing_ops",
            required_escalation_team="billing_ops",
            must_close=False,
            required_kb_article_ids={"KB-REFUND-01"},
            required_reply_phrases=[
                "prorated",
                "based on your usage",
                "billing team",
            ],
            forbidden_reply_phrases=["full refund approved", "guaranteed full refund"],
        ),
    )

    t3 = TaskSpec(
        task_id="account_compromise_signals",
        title="Suspected Account Compromise With Conflicting Signals",
        difficulty="hard",
        instructions=(
            "Prioritize security risk, escalate to security, avoid unsafe closure, "
            "send customer-safe response, and capture key internal security facts."
        ),
        max_steps=12,
        ticket=Ticket(
            ticket_id="T-3307",
            subject="Can not access account after unusual billing change",
            body=(
                "Saw login from unknown country, billing card changed, and now account locked. "
                "Please send direct reset link immediately."
            ),
            priority="normal",
        ),
        customer=CustomerProfile(
            customer_id="C-GAMMA",
            company_name="Gamma Systems",
            plan="enterprise",
        ),
        kb_articles=[
            KnowledgeBaseArticle(
                article_id="KB-SEC-01",
                title="Suspicious Login Escalation",
                content="Collect facts, lock risky actions, escalate to security immediately.",
                keywords=["security", "compromise", "suspicious", "billing change"],
            ),
            KnowledgeBaseArticle(
                article_id="KB-RESET-01",
                title="Secure Password Reset Flow",
                content="Identity checks required before reset links are sent.",
                keywords=["password", "reset", "identity"],
            ),
        ],
        expected=ExpectedResolution(
            required_priority="critical",
            required_tags={"security", "account_compromise"},
            required_team="trust_safety",
            required_escalation_team="security_incident",
            must_close=False,
            required_kb_article_ids={"KB-SEC-01"},
            required_reply_phrases=[
                "we have escalated this to our security team",
                "we cannot provide a reset link until verification",
                "please confirm recent account activity",
            ],
            forbidden_reply_phrases=["here is a reset link", "issue resolved and closed"],
            require_internal_note=True,
        ),
    )

    return {task.task_id: task for task in [t1, t2, t3]}


TASK_ORDER = [
    "password_reset_triage",
    "billing_refund_policy",
    "account_compromise_signals",
]
