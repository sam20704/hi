"""
agents/critic_agent.py

Critic Agent — Internal evidence auditor.

Uses Llama 3.2 to audit the consistency of deterministic
module outputs. Does NOT classify or score.

Responsibilities:
    1. Rule consistency checking
    2. Contradiction detection
    3. Reinforcement identification
    4. Confidence assessment
    5. Rerun recommendation
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.schemas.evidence import EvidenceCaseFile
from app.schemas.critic import CriticReport
from app.services.llm_clients import LlamaClient, get_critic_client, LLMFatalError


logger = logging.getLogger("forensic.critic")

# ── Paths ────────────────────────────────────────────
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_PROMPT_FILE = _PROMPT_DIR / "critic_prompt.txt"
_FEWSHOT_FILE = _PROMPT_DIR / "fewshot_examples.json"


# ═══════════════════════════════════════════════════════
# PROMPT LOADER
# ═══════════════════════════════════════════════════════

class PromptLoader:
    """
    Loads and caches prompt template + few-shot examples.
    Loaded once at first use, reused across requests.
    """

    _template: Optional[str] = None
    _fewshots: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def get_template(cls) -> str:
        if cls._template is None:
            if not _PROMPT_FILE.exists():
                raise FileNotFoundError(
                    f"Critic prompt not found: {_PROMPT_FILE}"
                )
            cls._template = _PROMPT_FILE.read_text(encoding="utf-8")
            logger.info(f"Loaded critic prompt ({len(cls._template)} chars)")
        return cls._template

    @classmethod
    def get_fewshots(cls) -> List[Dict[str, Any]]:
        if cls._fewshots is None:
            if not _FEWSHOT_FILE.exists():
                raise FileNotFoundError(
                    f"Few-shot examples not found: {_FEWSHOT_FILE}"
                )
            raw = json.loads(_FEWSHOT_FILE.read_text(encoding="utf-8"))
            if not isinstance(raw, list) or len(raw) == 0:
                raise ValueError("Few-shot file must be a non-empty list")
            cls._fewshots = raw
            logger.info(f"Loaded {len(cls._fewshots)} few-shot examples")
        return cls._fewshots

    @classmethod
    def clear_cache(cls):
        """Force reload on next access. Useful for testing."""
        cls._template = None
        cls._fewshots = None


# ═══════════════════════════════════════════════════════
# FEW-SHOT FORMATTER
# ═══════════════════════════════════════════════════════

def format_fewshot_examples(examples: List[Dict[str, Any]]) -> str:
    """
    Format few-shot examples into a clean text block
    for injection into the system prompt.

    Each example shows:
        - Label (what this case demonstrates)
        - Input case file
        - Expected critic output
    """
    blocks = []

    for i, ex in enumerate(examples, 1):
        label = ex.get("label", f"Example {i}")
        input_json = json.dumps(ex["input"], indent=2)
        output_json = json.dumps(ex["expected_output"], indent=2)

        block = (
            f"--- Example {i}: {label} ---\n"
            f"\n"
            f"Case File:\n"
            f"{input_json}\n"
            f"\n"
            f"Correct Critic Output:\n"
            f"{output_json}\n"
        )
        blocks.append(block)

    return "\n".join(blocks)


# ═══════════════════════════════════════════════════════
# CASE FILE SERIALIZER
# ═══════════════════════════════════════════════════════

def serialize_case_file(case: EvidenceCaseFile) -> str:
    """
    Convert validated case file to clean JSON string for LLM input.

    Uses model_dump to ensure Pydantic serialization rules apply.
    Excludes None values for cleaner prompts.
    """
    data = case.model_dump(exclude_none=True)
    return json.dumps(data, indent=2)


# ═══════════════════════════════════════════════════════
# PRE-FLIGHT VALIDATION
# ═══════════════════════════════════════════════════════

def preflight_check(case: EvidenceCaseFile) -> Optional[str]:
    """
    Quick deterministic sanity checks before calling LLM.

    Returns:
        None if all checks pass.
        Warning string if something is unusual.
    """
    warnings = []

    # Check: sum matches deterministic score
    raw_sum = (
        case.metadata.score
        + case.font.score
        + case.compression.score
    )
    expected_score = min(raw_sum, 10)

    if case.deterministic_score != expected_score:
        warnings.append(
            f"Score mismatch: modules sum to {raw_sum}, "
            f"expected min({raw_sum},10)={expected_score}, "
            f"but deterministic_score={case.deterministic_score}"
        )

    # Check: any module has high score but no signals
    for name, module in [
        ("metadata", case.metadata),
        ("font", case.font),
        ("compression", case.compression),
    ]:
        if module.score >= 5 and len(module.signals) == 0:
            warnings.append(
                f"{name} scores {module.score} but has no signals"
            )

    # Check: any module has zero score but many signals
    for name, module in [
        ("metadata", case.metadata),
        ("font", case.font),
        ("compression", case.compression),
    ]:
        if module.score == 0 and len(module.signals) >= 3:
            warnings.append(
                f"{name} scores 0 but has {len(module.signals)} signals"
            )

    if warnings:
        return "; ".join(warnings)
    return None


# ═══════════════════════════════════════════════════════
# CRITIC AGENT
# ═══════════════════════════════════════════════════════

class CriticAgent:
    """
    Forensic evidence auditor.

    Receives: EvidenceCaseFile (deterministic output)
    Returns: CriticReport (audit findings)

    Uses Llama 3.2 for reasoning.
    Does NOT classify, score, or override.

    Usage:
        agent = CriticAgent()
        report = await agent.audit(case_file)
    """

    def __init__(self, client: Optional[LlamaClient] = None):
        """
        Args:
            client: Optional LlamaClient override (for testing).
                    If None, uses singleton from factory.
        """
        self._client = client

    @property
    def client(self) -> LlamaClient:
        if self._client is None:
            self._client = get_critic_client()
        return self._client

    def _build_system_prompt(self) -> str:
        """
        Assemble system prompt from template + few-shot examples.
        """
        template = PromptLoader.get_template()
        examples = PromptLoader.get_fewshots()
        formatted_examples = format_fewshot_examples(examples)

        return template.replace("{few_shot_examples}", formatted_examples)

    def _build_user_prompt(
        self,
        case: EvidenceCaseFile,
        preflight_warning: Optional[str] = None,
    ) -> str:
        """
        Build user-facing prompt with the case file to analyze.
        Optionally includes preflight warnings as context.
        """
        case_json = serialize_case_file(case)

        parts = [
            "Analyze the following case file and produce your audit report.",
            "",
            "Case File:",
            case_json,
        ]

        if preflight_warning:
            parts.extend([
                "",
                "⚠ PREFLIGHT WARNINGS (detected before your analysis):",
                preflight_warning,
                "",
                "Consider these warnings in your audit.",
            ])

        return "\n".join(parts)

    async def audit(self, case: EvidenceCaseFile) -> CriticReport:
        """
        Run the full critic audit pipeline.

        Steps:
            1. Preflight validation (deterministic)
            2. Build prompts (system + user)
            3. Call Llama 3.2
            4. Return validated CriticReport

        Args:
            case: Validated EvidenceCaseFile

        Returns:
            CriticReport — validated audit findings

        Raises:
            LLMFatalError: if all retries exhausted
            FileNotFoundError: if prompt files missing
        """
        logger.info(f"[{case.case_id}] Starting critic audit")

        # ── Step 1: Preflight ──
        preflight_warning = preflight_check(case)
        if preflight_warning:
            logger.warning(
                f"[{case.case_id}] Preflight: {preflight_warning}"
            )

        # ── Step 2: Build prompts ──
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(case, preflight_warning)

        logger.debug(
            f"[{case.case_id}] System prompt: {len(system_prompt)} chars | "
            f"User prompt: {len(user_prompt)} chars"
        )

        # ── Step 3: Call LLM ──
        try:
            report: CriticReport = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=CriticReport,
            )
        except LLMFatalError:
            logger.error(f"[{case.case_id}] Critic audit FAILED — LLM fatal error")
            raise

        # ── Step 4: Post-validation logging ──
        contradiction_count = len(report.contradictions)
        reinforcement_count = len(report.reinforcement)

        logger.info(
            f"[{case.case_id}] Critic audit complete | "
            f"consistent={report.rule_consistency} | "
            f"contradictions={contradiction_count} | "
            f"reinforcements={reinforcement_count} | "
            f"confidence={report.confidence:.2f} ({report.confidence_level.value}) | "
            f"rerun={report.rerun_recommended}"
        )

        return report
