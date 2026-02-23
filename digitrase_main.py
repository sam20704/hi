"""
app/main.py

Forensic Document Validation API.

Single endpoint that receives deterministic module scores
and returns an agentic forensic verdict with explanation.

Architecture:
    POST /validate → ForensicValidator → PipelineResult → JSON

Production considerations:
    - Startup/shutdown lifecycle for LLM clients
    - Structured error responses
    - Request validation via Pydantic
    - Health check endpoint
    - CORS disabled by default (enable per deployment)
    - No sensitive data in responses
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.evidence import EvidenceCaseFile
from app.services.validator import validate_case, get_validator, PipelineError
from app.services.llm_clients import shutdown_clients


# ═══════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format=(
        "%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("forensic.api")


# ═══════════════════════════════════════════════════════
# APPLICATION LIFECYCLE
# ═══════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle.

    Startup:
        - Initialize validator (creates LLM clients)
        - Log configuration

    Shutdown:
        - Close all LLM client connections gracefully
    """
    # ── Startup ──
    logger.info("═══ Forensic Validation API starting ═══")
    logger.info(f"Critic model:     {settings.LLAMA_MODEL}")
    logger.info(f"Reflection model: {settings.CLAUDE_MODEL}")
    logger.info(f"Max retries:      {settings.MAX_RETRIES}")
    logger.info(f"Log level:        {settings.LOG_LEVEL}")

    # Eagerly initialize validator + clients
    get_validator()

    logger.info("═══ API ready ═══")

    yield

    # ── Shutdown ──
    logger.info("═══ Shutting down ═══")
    await shutdown_clients()
    logger.info("═══ Shutdown complete ═══")


# ═══════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════

app = FastAPI(
    title="Forensic Document Validation API",
    description=(
        "Agentic validation layer for document tampering detection. "
        "Receives deterministic module scores and produces "
        "forensic verdicts with reasoning and explanation."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ═══════════════════════════════════════════════════════
# ERROR RESPONSES
# ═══════════════════════════════════════════════════════

class ErrorResponse:
    """Standardized error response builder."""

    @staticmethod
    def validation_error(detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "validation_error",
                "detail": detail,
            },
        )

    @staticmethod
    def pipeline_error(
        case_id: str,
        stage: str,
        detail: str,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "error": "pipeline_error",
                "case_id": case_id,
                "failed_stage": stage,
                "detail": detail,
            },
        )

    @staticmethod
    def internal_error(detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "internal_error",
                "detail": detail,
            },
        )


# ═══════════════════════════════════════════════════════
# MIDDLEWARE: Request Logging
# ═══════════════════════════════════════════════════════

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log every request with timing.
    No sensitive data logged.
    """
    start = time.monotonic()
    method = request.method
    path = request.url.path

    response = await call_next(request)

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        f"{method} {path} → {response.status_code} "
        f"({duration_ms:.0f}ms)"
    )

    return response


# ═══════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
)
async def health():
    """
    Basic health check.

    Returns:
        200 with status and model configuration.
    """
    return {
        "status": "healthy",
        "models": {
            "critic": settings.LLAMA_MODEL,
            "reflection": settings.CLAUDE_MODEL,
        },
    }


@app.post(
    "/validate",
    tags=["Validation"],
    summary="Validate a document case file",
    response_description="Forensic verdict with explanation and evidence",
)
async def validate_document(case: EvidenceCaseFile):
    """
    Run forensic validation on a deterministic case file.

    **Flow:**
    1. Receives module scores + signals from deterministic engine
    2. Critic Agent (Llama 3.2) audits evidence consistency
    3. Reflection Agent (Claude) produces final verdict + explanation
    4. Returns complete result with audit trail

    **Input:**
    - `case_id`: Unique identifier
    - `metadata`: Module result (score + signals)
    - `font`: Module result (score + signals)
    - `compression`: Module result (score + signals)
    - `qr`: Optional module result
    - `deterministic_score`: Pre-computed score (0-10)
    - `priority`: Pre-computed priority (Low/Medium/High)

    **Output:**
    - `verdict`: Final forensic judgment
    - `critic_report`: Internal audit findings
    - `duration_ms`: Processing time
    - `success`: True/False

    **Error codes:**
    - `422`: Invalid input (schema violation)
    - `502`: LLM pipeline failure
    - `500`: Unexpected server error
    """
    try:
        result = await validate_case(case)
        return result.to_dict()

    except PipelineError as e:
        logger.error(
            f"[{e.case_id}] Pipeline error at {e.stage}: {e.cause}"
        )
        return ErrorResponse.pipeline_error(
            case_id=e.case_id,
            stage=e.stage,
            detail=str(e.cause),
        )

    except Exception as e:
        logger.error(
            f"Unexpected error during validation: {e}",
            exc_info=True,
        )
        return ErrorResponse.internal_error(
            detail="An unexpected error occurred. Check server logs.",
        )


# ═══════════════════════════════════════════════════════
# PYDANTIC VALIDATION ERROR HANDLER
# ═══════════════════════════════════════════════════════

from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """
    Custom handler for Pydantic validation errors.

    Produces cleaner error messages than FastAPI default.
    Catches:
        - Missing required fields
        - Invalid field types
        - Enum mismatches
        - Priority/score alignment failures
    """
    errors = []
    for error in exc.errors():
        loc = " → ".join(str(l) for l in error["loc"])
        msg = error["msg"]
        errors.append(f"{loc}: {msg}")

    detail = "; ".join(errors)

    logger.warning(f"Validation error: {detail}")

    return ErrorResponse.validation_error(detail=detail)
