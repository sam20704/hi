"""
agents/reflection_agent.py

Reflection Agent — Final forensic judge.

Uses Claude to synthesize:
    - Deterministic case file
    - Critic audit report

Into a final ForensicVerdict with explanation and evidence trace.

Does NOT rescore. Does NOT override deterministic rules.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from app.schemas.evidence import EvidenceCaseFile
from app.schemas.critic import CriticReport
from app.schemas.reflection import ForensicVerdict
from app.services.llm_clients import ClaudeClient, get_reflection_client, LLMFatalError


logger = logging.getLogger("forensic.reflection")

# ── Paths ────────────────────────────────────────────
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_PROMPT_FILE = _PROMPT_DIR / "reflection_prompt.txt"


# ═══════════════════════════════════════════════════════
# PROMPT LOADER
# ═══════════════════════════════════════════════════════

class ReflectionPromptLoader:
    """
    Loads and caches reflection system prompt.
    """

    _template: Optional[str] = None

    @classmethod
    def get_template(cls) -> str:
        if cls._template is None:
            if not _PROMPT_FILE.exists():
                raise FileNotFoundError(
                    f"Reflection prompt not found: {_PROMPT_FILE}"
                )
            cls._template = _PROMPT_FILE.read_text(encoding="utf-8")
            logger.info(
                f"Loaded reflection prompt ({len(cls._template)} chars)"
            )
        return cls._template

    @classmethod
    def clear_cache(cls):
        cls._template = None


# ═══════════════════════════════════════════════════════
# INPUT SERIALIZER
# ═══════════════════════════════════════════════════════

def build_reflection_input(
    case: EvidenceCaseFile,
    critic_report: CriticReport,
) -> str:
    """
    Serialize both inputs into a single structured prompt.

    Keeps case file and critic report clearly separated
    so Claude can reference each independently.
    """
    case_data = case.model_dump(exclude_none=True)
    critic_data = critic_report.model_dump()

    # Convert enums to strings for clean JSON
    combined = {
        "case_file": case_data,
        "critic_report": critic_data,
    }

    return json.dumps(combined, indent=2, default=str)


# ═══════════════════════════════════════════════════════
# PRE-VERDICT CHECKS
# ═══════════════════════════════════════════════════════

def should_flag_for_review(
    case: EvidenceCaseFile,
    critic: CriticReport,
) -> Optional[str]:
    """
    Deterministic pre-check: should this case be flagged
    for human review regardless of LLM output?

    Returns:
        Reason string if flagging recommended, None otherwise.
    """
    reasons = []

    # Low critic confidence
    if critic.confidence < 0.5:
        reasons.append(
            f"Critic confidence is low ({critic.confidence:.2f})"
        )

    # Critic recommends rerun
    if critic.rerun_recommended:
        reasons.append("Critic recommended deterministic rerun")

    # High-impact contradictions
    high_contradictions = [
        c for c in critic.contradictions
        if c.impact.value == "High"
    ]
    if high_contradictions:
        reasons.append(
            f"{len(high_contradictions)} high-impact contradiction(s) found"
        )

    # Borderline score
    if case.deterministic_score in (4, 5):
        reasons.append(
            f"Borderline score ({case.deterministic_score}) — "
            f"near classification boundary"
        )

    # Sparse evidence: only one module has signals
    modules_with_signals = sum(
        1 for m in [case.metadata, case.font, case.compression]
        if len(m.signals) > 0
    )
    if modules_with_signals <= 1 and case.deterministic_score >= 4:
        reasons.append(
            f"Only {modules_with_signals} module(s) produced signals — "
            f"sparse evidence for score {case.deterministic_score}"
        )

    # Rule inconsistency detected by critic
    if not critic.rule_consistency:
        reasons.append("Critic detected rule inconsistency")

    if reasons:
        return "; ".join(reasons)
    return None


# ═══════════════════════════════════════════════════════
# POST-VERDICT VALIDATION
# ═══════════════════════════════════════════════════════

def validate_verdict(
    verdict: ForensicVerdict,
    case: EvidenceCaseFile,
    review_reason: Optional[str],
) -> ForensicVerdict:
    """
    Enforce hard constraints the LLM must not violate.

    Even with schema enforcement, the LLM might return
    a valid schema with wrong values. This catches that.

    Mutates and returns the verdict.
    """
    corrections = []

    # ── Enforce deterministic_score passthrough ──
    if verdict.deterministic_score != case.deterministic_score:
        corrections.append(
            f"Corrected deterministic_score: "
            f"{verdict.deterministic_score} → {case.deterministic_score}"
        )
        verdict.deterministic_score = case.deterministic_score

    # ── Enforce severity matches score ──
    expected_severity = case.priority.value  # Already validated in schema
    if verdict.severity.value != expected_severity:
        corrections.append(
            f"Corrected severity: "
            f"{verdict.severity.value} → {expected_severity}"
        )
        verdict.severity = expected_severity

    # ── Enforce case_id passthrough ──
    if verdict.case_id != case.case_id:
        corrections.append(
            f"Corrected case_id: {verdict.case_id} → {case.case_id}"
        )
        verdict.case_id = case.case_id

    # ── Enforce review flag from deterministic pre-check ──
    if review_reason and not verdict.flagged_for_human_review:
        corrections.append("Forced flagged_for_human_review = true")
        verdict.flagged_for_human_review = True
        verdict.review_reason = review_reason

    # ── Log corrections ──
    if corrections:
        logger.warning(
            f"[{case.case_id}] Post-verdict corrections: "
            f"{'; '.join(corrections)}"
        )

    return verdict


# ═══════════════════════════════════════════════════════
# REFLECTION AGENT
# ═══════════════════════════════════════════════════════

class ReflectionAgent:
    """
    Final forensic judge.

    Receives: EvidenceCaseFile + CriticReport
    Returns: ForensicVerdict

    Uses Claude for reasoning and explanation.
    Does NOT rescore or override deterministic rules.

    Usage:
        agent = ReflectionAgent()
        verdict = await agent.judge(case_file, critic_report)
    """

    def __init__(self, client: Optional[ClaudeClient] = None):
        """
        Args:
            client: Optional ClaudeClient override (for testing).
                    If None, uses singleton from factory.
        """
        self._client = client

    @property
    def client(self) -> ClaudeClient:
        if self._client is None:
            self._client = get_reflection_client()
        return self._client

    def _build_system_prompt(self) -> str:
        return ReflectionPromptLoader.get_template()

    def _build_user_prompt(
        self,
        case: EvidenceCaseFile,
        critic_report: CriticReport,
        review_hint: Optional[str] = None,
    ) -> str:
        """
        Build user prompt with case file + critic report.
        """
        combined_json = build_reflection_input(case, critic_report)

        parts = [
            "Review the following case file and critic audit report.",
            "Produce your final forensic verdict.",
            "",
            combined_json,
        ]

        if review_hint:
            parts.extend([
                "",
                "⚠ PRE-CHECK FLAGS (deterministic, not from critic):",
                review_hint,
                "",
                "Consider flagging this case for human review.",
            ])

        # Inject key constraints as final reminder
        parts.extend([
            "",
            "REMINDERS:",
            f"- case_id MUST be: {case.case_id}",
            f"- deterministic_score MUST be: {case.deterministic_score}",
            f"- severity MUST be: {case.priority.value}",
        ])

        return "\n".join(parts)

    async def judge(
        self,
        case: EvidenceCaseFile,
        critic_report: CriticReport,
    ) -> ForensicVerdict:
        """
        Run the full reflection pipeline.

        Steps:
            1. Pre-verdict review check (deterministic)
            2. Build prompts
            3. Call Claude
            4. Post-verdict validation (enforce hard constraints)
            5. Return validated ForensicVerdict

        Args:
            case: Validated EvidenceCaseFile
            critic_report: CriticReport from Critic Agent

        Returns:
            ForensicVerdict — validated final verdict

        Raises:
            LLMFatalError: if all retries exhausted
            FileNotFoundError: if prompt file missing
        """
        logger.info(f"[{case.case_id}] Starting reflection judgment")

        # ── Step 1: Deterministic review check ──
        review_reason = should_flag_for_review(case, critic_report)
        if review_reason:
            logger.info(
                f"[{case.case_id}] Pre-check flags: {review_reason}"
            )

        # ── Step 2: Build prompts ──
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            case, critic_report, review_reason
        )

        logger.debug(
            f"[{case.case_id}] System prompt: {len(system_prompt)} chars | "
            f"User prompt: {len(user_prompt)} chars"
        )

        # ── Step 3: Call Claude ──
        try:
            verdict: ForensicVerdict = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=ForensicVerdict,
            )
        except LLMFatalError:
            logger.error(
                f"[{case.case_id}] Reflection judgment FAILED — "
                f"LLM fatal error"
            )
            raise

        # ── Step 4: Post-verdict enforcement ──
        verdict = validate_verdict(verdict, case, review_reason)

        # ── Step 5: Final logging ──
        logger.info(
            f"[{case.case_id}] Verdict delivered | "
            f"tampered={verdict.tampered} | "
            f"severity={verdict.severity.value} | "
            f"confidence={verdict.confidence:.2f} "
            f"({verdict.confidence_level.value}) | "
            f"evidence_items={len(verdict.evidence)} | "
            f"flagged={verdict.flagged_for_human_review}"
        )

        return verdict
