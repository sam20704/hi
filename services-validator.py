"""
services/validator.py

Forensic Validation Orchestrator.

Chains:
    EvidenceCaseFile → CriticAgent → ReflectionAgent → ForensicVerdict

This is the ONLY entry point for the validation pipeline.
All consumers (API, CLI, tests) call this.

Design:
    - Deterministic rules are NEVER overridden
    - LLMs reason and explain, they don't score
    - Failures are classified (retryable vs fatal)
    - Every step is logged with case_id for audit trail
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass

from app.schemas.evidence import EvidenceCaseFile
from app.schemas.critic import CriticReport
from app.schemas.reflection import ForensicVerdict
from app.agents.critic_agent import CriticAgent
from app.agents.reflection_agent import ReflectionAgent
from app.services.llm_clients import LLMFatalError


logger = logging.getLogger("forensic.validator")


# ═══════════════════════════════════════════════════════
# PIPELINE RESULT
# ═══════════════════════════════════════════════════════

@dataclass
class PipelineResult:
    """
    Complete output from the validation pipeline.

    Contains all intermediate artifacts for:
        - API response
        - Audit trail
        - Debugging
        - Testing
    """

    # ── Core output ──
    verdict: ForensicVerdict

    # ── Intermediate artifacts ──
    critic_report: CriticReport

    # ── Pipeline metadata ──
    case_id: str
    duration_ms: float
    success: bool

    # ── Error info (only if success=False) ──
    error: Optional[str] = None
    failed_stage: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Serialize for API response.

        Returns only what consumers need.
        Critic report is included for transparency.
        """
        result = {
            "case_id": self.case_id,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
            "verdict": self.verdict.model_dump(mode="json"),
            "critic_report": self.critic_report.model_dump(mode="json"),
        }

        if self.error:
            result["error"] = self.error
            result["failed_stage"] = self.failed_stage

        return result


# ═══════════════════════════════════════════════════════
# PIPELINE ERROR
# ═══════════════════════════════════════════════════════

class PipelineError(Exception):
    """
    Raised when the pipeline fails irrecoverably.

    Attributes:
        case_id: Which case failed
        stage: Which stage failed (critic / reflection)
        cause: Original exception
    """

    def __init__(self, case_id: str, stage: str, cause: Exception):
        self.case_id = case_id
        self.stage = stage
        self.cause = cause
        super().__init__(
            f"[{case_id}] Pipeline failed at {stage}: {cause}"
        )


# ═══════════════════════════════════════════════════════
# FORENSIC VALIDATOR (Orchestrator)
# ═══════════════════════════════════════════════════════

class ForensicValidator:
    """
    Main orchestrator for the forensic validation pipeline.

    Flow:
        1. Receive EvidenceCaseFile (deterministic scores + signals)
        2. Run CriticAgent (Llama 3.2) → CriticReport
        3. Run ReflectionAgent (Claude) → ForensicVerdict
        4. Return PipelineResult with all artifacts

    Usage:
        validator = ForensicValidator()
        result = await validator.validate(case_file)

        # Access outputs
        result.verdict.tampered          # True/False
        result.verdict.severity          # High/Medium/Low
        result.verdict.explanation        # Forensic narrative
        result.critic_report.contradictions  # What critic found

    Thread safety:
        ForensicValidator is stateless.
        Safe to share across async tasks.
        Agents use singleton LLM clients internally.
    """

    def __init__(
        self,
        critic: Optional[CriticAgent] = None,
        reflection: Optional[ReflectionAgent] = None,
    ):
        """
        Args:
            critic: Optional CriticAgent override (for testing).
            reflection: Optional ReflectionAgent override (for testing).
        """
        self._critic = critic or CriticAgent()
        self._reflection = reflection or ReflectionAgent()

    async def validate(
        self,
        case: EvidenceCaseFile,
    ) -> PipelineResult:
        """
        Run the full validation pipeline.

        Steps:
            1. Critic audit (Llama 3.2)
            2. Reflection judgment (Claude)
            3. Package results

        Args:
            case: Validated EvidenceCaseFile from deterministic engine

        Returns:
            PipelineResult containing verdict + critic report + metadata

        Raises:
            PipelineError: if any stage fails irrecoverably
        """
        start_time = time.monotonic()

        logger.info(
            f"[{case.case_id}] ═══ Pipeline started ═══ | "
            f"score={case.deterministic_score} | "
            f"priority={case.priority.value}"
        )

        # ── Stage 1: Critic ──
        critic_report = await self._run_critic(case)

        # ── Stage 2: Reflection ──
        verdict = await self._run_reflection(case, critic_report)

        # ── Package result ──
        duration_ms = (time.monotonic() - start_time) * 1000

        result = PipelineResult(
            verdict=verdict,
            critic_report=critic_report,
            case_id=case.case_id,
            duration_ms=duration_ms,
            success=True,
        )

        logger.info(
            f"[{case.case_id}] ═══ Pipeline complete ═══ | "
            f"tampered={verdict.tampered} | "
            f"severity={verdict.severity.value} | "
            f"confidence={verdict.confidence:.2f} | "
            f"flagged={verdict.flagged_for_human_review} | "
            f"duration={duration_ms:.0f}ms"
        )

        return result

    async def _run_critic(
        self,
        case: EvidenceCaseFile,
    ) -> CriticReport:
        """
        Execute critic stage with error handling.

        Raises:
            PipelineError if critic fails.
        """
        logger.info(f"[{case.case_id}] Stage 1/2: Critic audit")

        try:
            report = await self._critic.audit(case)
            return report

        except LLMFatalError as e:
            logger.error(
                f"[{case.case_id}] Critic stage FAILED: {e}"
            )
            raise PipelineError(
                case_id=case.case_id,
                stage="critic",
                cause=e,
            )

        except FileNotFoundError as e:
            logger.error(
                f"[{case.case_id}] Critic prompt missing: {e}"
            )
            raise PipelineError(
                case_id=case.case_id,
                stage="critic",
                cause=e,
            )

        except Exception as e:
            logger.error(
                f"[{case.case_id}] Critic unexpected error: {e}",
                exc_info=True,
            )
            raise PipelineError(
                case_id=case.case_id,
                stage="critic",
                cause=e,
            )

    async def _run_reflection(
        self,
        case: EvidenceCaseFile,
        critic_report: CriticReport,
    ) -> ForensicVerdict:
        """
        Execute reflection stage with error handling.

        Raises:
            PipelineError if reflection fails.
        """
        logger.info(f"[{case.case_id}] Stage 2/2: Reflection judgment")

        try:
            verdict = await self._reflection.judge(case, critic_report)
            return verdict

        except LLMFatalError as e:
            logger.error(
                f"[{case.case_id}] Reflection stage FAILED: {e}"
            )
            raise PipelineError(
                case_id=case.case_id,
                stage="reflection",
                cause=e,
            )

        except FileNotFoundError as e:
            logger.error(
                f"[{case.case_id}] Reflection prompt missing: {e}"
            )
            raise PipelineError(
                case_id=case.case_id,
                stage="reflection",
                cause=e,
            )

        except Exception as e:
            logger.error(
                f"[{case.case_id}] Reflection unexpected error: {e}",
                exc_info=True,
            )
            raise PipelineError(
                case_id=case.case_id,
                stage="reflection",
                cause=e,
            )


# ═══════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════

# Shared validator instance (stateless, safe to reuse)
_validator: Optional[ForensicValidator] = None


def get_validator() -> ForensicValidator:
    """
    Get or create singleton ForensicValidator.

    Used by FastAPI endpoint and CLI.
    """
    global _validator
    if _validator is None:
        _validator = ForensicValidator()
        logger.info("ForensicValidator initialized")
    return _validator


async def validate_case(case: EvidenceCaseFile) -> PipelineResult:
    """
    One-liner convenience function.

    Usage:
        from app.services.validator import validate_case

        result = await validate_case(case_file)
    """
    validator = get_validator()
    return await validator.validate(case)
