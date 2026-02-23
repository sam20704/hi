"""
tests/test_pipeline.py

Offline deterministic test suite for forensic validation pipeline.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from app.schemas.evidence import EvidenceCaseFile, ModuleResult, Priority
from app.schemas.critic import (
    CriticReport,
    Contradiction,
    ContradictionType,
    ContradictionImpact,
    ConfidenceLevel,
)
from app.schemas.reflection import (
    ForensicVerdict,
    Severity,
    EvidenceItem,
    EvidenceSource,
    EvidenceWeight,
)
from app.agents.critic_agent import preflight_check, serialize_case_file, PromptLoader
from app.agents.reflection_agent import should_flag_for_review, validate_verdict
from app.services.validator import ForensicValidator, PipelineError, PipelineResult
from app.services.llm_clients import LLMFatalError
from app.agents.critic_agent import CriticAgent
from app.agents.reflection_agent import ReflectionAgent


# ───────────────────────── FIXTURES ─────────────────────────

@pytest.fixture
def clean_case():
    return EvidenceCaseFile(
        case_id="CLEAN",
        metadata=ModuleResult(score=1, signals=["single_tool"]),
        font=ModuleResult(score=0, signals=[]),
        compression=ModuleResult(score=1, signals=["minor_compression"]),
        deterministic_score=2,
        priority=Priority.Low,
    )


@pytest.fixture
def tampered_case():
    return EvidenceCaseFile(
        case_id="TAMPER",
        metadata=ModuleResult(score=6, signals=["tool_mismatch"]),
        font=ModuleResult(score=5, signals=["mixed_fonts"]),
        compression=ModuleResult(score=4, signals=["double_compression"]),
        deterministic_score=10,
        priority=Priority.High,
    )


@pytest.fixture
def mock_critic_report():
    return CriticReport(
        rule_consistency=True,
        contradictions=[],
        reinforcement=["All modules reinforce"],
        confidence=0.95,
        confidence_level=ConfidenceLevel.VERY_HIGH,
        confidence_reason="Strong agreement",
        audit_notes="OK",
        rerun_recommended=False,
    )


@pytest.fixture
def mock_verdict(tampered_case):
    return ForensicVerdict(
        case_id=tampered_case.case_id,
        tampered=True,
        severity=Severity.High,
        deterministic_score=10,
        confidence=0.93,
        confidence_level=ConfidenceLevel.VERY_HIGH,
        explanation="Strong tampering evidence.",
        evidence=[
            EvidenceItem(
                source=EvidenceSource.METADATA,
                finding="Multiple tools detected",
                weight=EvidenceWeight.SUPPORTING,
            )
        ],
        flagged_for_human_review=False,
    )


# ───────────────────────── SCHEMA TESTS ─────────────────────────

def test_priority_alignment():
    with pytest.raises(ValidationError):
        EvidenceCaseFile(
            case_id="FAIL",
            metadata=ModuleResult(score=5, signals=[]),
            font=ModuleResult(score=4, signals=[]),
            compression=ModuleResult(score=0, signals=[]),
            deterministic_score=9,
            priority=Priority.Low,
        )


# ───────────────────────── PREFLIGHT ─────────────────────────

def test_preflight_clean(clean_case):
    assert preflight_check(clean_case) is None


def test_preflight_detects_score_mismatch():
    case = EvidenceCaseFile(
        case_id="BAD",
        metadata=ModuleResult(score=3, signals=["a"]),
        font=ModuleResult(score=2, signals=["b"]),
        compression=ModuleResult(score=0, signals=[]),
        deterministic_score=7,
        priority=Priority.Medium,
    )
    assert preflight_check(case) is not None


# ───────────────────────── REFLECTION FLAGS ─────────────────────────

def test_flag_low_confidence(tampered_case):
    critic = CriticReport(
        rule_consistency=True,
        contradictions=[],
        reinforcement=[],
        confidence=0.4,
        confidence_level=ConfidenceLevel.LOW,
        confidence_reason="weak",
        audit_notes="",
        rerun_recommended=False,
    )
    assert should_flag_for_review(tampered_case, critic) is not None


# ───────────────────────── POST VERDICT ─────────────────────────

def test_validate_verdict_score_fix(tampered_case):
    verdict = ForensicVerdict(
        case_id="wrong",
        tampered=True,
        severity=Severity.Low,
        deterministic_score=3,
        confidence=0.5,
        confidence_level=ConfidenceLevel.MEDIUM,
        explanation="bad",
        evidence=[
            EvidenceItem(
                source=EvidenceSource.FONT,
                finding="x",
                weight=EvidenceWeight.SUPPORTING,
            )
        ],
    )

    corrected = validate_verdict(verdict, tampered_case, None)

    assert corrected.case_id == tampered_case.case_id
    assert corrected.deterministic_score == 10
    assert corrected.severity == Severity.High


# ───────────────────────── SERIALIZATION ─────────────────────────

def test_serialize(clean_case):
    data = json.loads(serialize_case_file(clean_case))
    assert "qr" not in data
    assert data["case_id"] == "CLEAN"


# ───────────────────────── FULL PIPELINE ─────────────────────────

@pytest.mark.asyncio
async def test_pipeline(clean_case, mock_critic_report, mock_verdict):
    critic = CriticAgent.__new__(CriticAgent)
    critic.audit = AsyncMock(return_value=mock_critic_report)

    reflection = ReflectionAgent.__new__(ReflectionAgent)
    reflection.judge = AsyncMock(return_value=mock_verdict)

    validator = ForensicValidator(critic=critic, reflection=reflection)

    result = await validator.validate(clean_case)

    assert result.success is True
    assert result.verdict.tampered is True
    assert isinstance(result.duration_ms, float)


# ───────────────────────── ERROR PATH ─────────────────────────

@pytest.mark.asyncio
async def test_critic_failure(clean_case):
    critic = CriticAgent.__new__(CriticAgent)
    critic.audit = AsyncMock(side_effect=LLMFatalError("boom"))

    reflection = ReflectionAgent.__new__(ReflectionAgent)

    validator = ForensicValidator(critic=critic, reflection=reflection)

    with pytest.raises(PipelineError):
        await validator.validate(clean_case)


# ───────────────────────── PROMPT LOADER ─────────────────────────

def test_missing_fewshots_returns_empty():
    with patch(
        "app.agents.critic_agent._FEWSHOT_FILE",
        MagicMock(exists=MagicMock(return_value=False)),
    ):
        PromptLoader.clear_cache()
        shots = PromptLoader.get_fewshots()
        assert shots == []


# ───────────────────────── PIPELINE RESULT ─────────────────────────

def test_pipeline_result_to_dict(mock_verdict, mock_critic_report):
    result = PipelineResult(
        verdict=mock_verdict,
        critic_report=mock_critic_report,
        case_id="X",
        duration_ms=100,
        success=True,
    )

    d = result.to_dict()
    assert d["success"] is True
