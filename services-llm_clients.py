"""
services/llm_clients.py

Production-grade LLM clients for forensic document validation.

Architecture:
    Critic Agent   → Llama 3.2 (via OpenAI-compatible API)
    Reflection Agent → Claude   (via Anthropic API)

Design principles:
    1. Schema-enforced responses (reject hallucinated fields)
    2. Self-healing retry (feed validation errors back to LLM)
    3. Robust JSON extraction (handles markdown wrapping)
    4. Classified errors (retryable vs fatal)
    5. Audit-grade request tracking
    6. Zero chain-of-thought leakage
"""

import json
import re
import uuid
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional

from pydantic import BaseModel, ValidationError

from openai import (
    AsyncOpenAI,
    APIError as OpenAIAPIError,
    RateLimitError as OpenAIRateLimitError,
    APITimeoutError as OpenAITimeoutError,
    APIConnectionError as OpenAIConnectionError,
)
from anthropic import (
    AsyncAnthropic,
    APIError as AnthropicAPIError,
    RateLimitError as AnthropicRateLimitError,
    APITimeoutError as AnthropicTimeoutError,
    APIConnectionError as AnthropicConnectionError,
)

from app.config import settings


logger = logging.getLogger("forensic.llm")
T = TypeVar("T", bound=BaseModel)


# ═══════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════

class LLMError(Exception):
    """Base error for all LLM operations."""
    pass


class LLMRetryableError(LLMError):
    """Transient error — safe to retry (rate limit, timeout, 5xx)."""
    pass


class LLMFatalError(LLMError):
    """Permanent error — do NOT retry (auth, bad model, etc)."""
    pass


class LLMParsingError(LLMError):
    """Response could not be parsed into valid JSON."""
    pass


class LLMSchemaViolation(LLMError):
    """JSON parsed but failed Pydantic schema validation."""
    pass


# ═══════════════════════════════════════════════════════
# JSON EXTRACTION
# ═══════════════════════════════════════════════════════

def extract_json(raw_text: str) -> dict:
    """
    Robustly extract JSON object from LLM response.

    Handles:
        1. Raw JSON string
        2. Markdown-wrapped  ```json ... ```
        3. JSON embedded in surrounding text
        4. Nested brace matching

    Raises:
        LLMParsingError if no valid JSON found.
    """
    text = raw_text.strip()

    # ── Attempt 1: Direct parse ──
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Attempt 2: Markdown code block ──
    md_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```",
        text,
        re.DOTALL,
    )
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # ── Attempt 3: First balanced { ... } block ──
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        in_string = False
        escape_next = False

        for i in range(brace_start, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise LLMParsingError(
        f"No valid JSON found in response (first 200 chars): "
        f"{text[:200]}"
    )


# ═══════════════════════════════════════════════════════
# BASE CLIENT
# ═══════════════════════════════════════════════════════

class BaseLLMClient(ABC):
    """
    Abstract base for forensic LLM clients.

    Provides:
        - Schema-enforced generation
        - Self-healing retry on parse/validation failure
        - Exponential backoff on transient errors
        - Request-level audit tracking
    """

    def __init__(
        self,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: int,
        max_retries: int,
        retry_base_delay: float,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    @abstractmethod
    async def _raw_call(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
    ) -> str:
        """
        Execute raw API call. Returns raw text response.
        Must raise LLMRetryableError or LLMFatalError.
        """
        ...

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
    ) -> T:
        """
        Call LLM → extract JSON → validate against Pydantic schema.

        Self-healing: on parse/validation failure, feeds the error
        back to the LLM on retry so it can correct itself.

        Returns:
            Validated Pydantic model instance.

        Raises:
            LLMFatalError after all retries exhausted.
        """
        request_id = uuid.uuid4().hex[:8]
        schema_text = json.dumps(schema.model_json_schema(), indent=2)
        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # ── Build prompt (self-healing on retry) ──
                if attempt == 1:
                    effective_prompt = user_prompt
                else:
                    effective_prompt = (
                        f"{user_prompt}\n\n"
                        f"--- CORRECTION (attempt {attempt}/{self.max_retries}) ---\n"
                        f"Your previous response was invalid.\n"
                        f"Error: {last_error}\n"
                        f"Return ONLY valid JSON matching the schema. "
                        f"No markdown. No extra text."
                    )

                logger.info(
                    f"[{request_id}] LLM call | model={self.model} | "
                    f"attempt={attempt}/{self.max_retries}"
                )

                # ── Raw API call ──
                raw_response = await self._raw_call(
                    system_prompt=system_prompt,
                    user_prompt=effective_prompt,
                    schema_hint=schema_text,
                )

                # ── Extract JSON ──
                parsed = extract_json(raw_response)

                # ── Validate against Pydantic schema ──
                result = schema.model_validate(parsed)

                logger.info(
                    f"[{request_id}] Success | model={self.model} | "
                    f"attempt={attempt}"
                )
                return result

            except LLMParsingError as e:
                last_error = f"JSON extraction failed: {str(e)[:200]}"
                logger.warning(f"[{request_id}] {last_error}")

            except ValidationError as e:
                last_error = (
                    f"Schema validation failed: "
                    f"{e.error_count()} errors — {str(e)[:300]}"
                )
                logger.warning(f"[{request_id}] {last_error}")

            except LLMRetryableError as e:
                last_error = f"Transient error: {str(e)[:200]}"
                delay = self.retry_base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"[{request_id}] {last_error} | "
                    f"backing off {delay:.1f}s"
                )
                await asyncio.sleep(delay)

            except LLMFatalError:
                logger.error(f"[{request_id}] Fatal error — not retrying")
                raise

        raise LLMFatalError(
            f"[{request_id}] All {self.max_retries} attempts failed "
            f"for {self.model}. Last error: {last_error}"
        )


# ═══════════════════════════════════════════════════════
# LLAMA CLIENT (Critic Agent)
# ═══════════════════════════════════════════════════════

class LlamaClient(BaseLLMClient):
    """
    Llama 3.2 via OpenAI-compatible API.

    Supports: Together AI, Groq, Fireworks, vLLM, Ollama
    Uses response_format=json_object when available.
    """

    def __init__(self):
        super().__init__(
            model=settings.LLAMA_MODEL,
            max_tokens=settings.LLAMA_MAX_TOKENS,
            temperature=settings.LLAMA_TEMPERATURE,
            timeout=settings.LLAMA_TIMEOUT,
            max_retries=settings.MAX_RETRIES,
            retry_base_delay=settings.RETRY_BASE_DELAY,
        )
        self._client = AsyncOpenAI(
            api_key=settings.LLAMA_API_KEY,
            base_url=settings.LLAMA_BASE_URL,
            timeout=float(self.timeout),
        )

    async def _raw_call(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
    ) -> str:
        """Call Llama via OpenAI-compatible endpoint."""

        # Inject schema requirement into system prompt
        full_system = (
            f"{system_prompt}\n\n"
            f"RESPONSE FORMAT:\n"
            f"You MUST respond with valid JSON matching this exact schema:\n"
            f"{schema_hint}\n\n"
            f"Rules:\n"
            f"- Output ONLY the JSON object\n"
            f"- No markdown wrapping\n"
            f"- No extra text before or after\n"
            f"- All required fields must be present\n"
            f"- Enums must match exactly"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content

            if not content:
                raise LLMRetryableError("Empty response from Llama")

            # Log usage (no sensitive data)
            if response.usage:
                logger.debug(
                    f"Llama usage: "
                    f"prompt={response.usage.prompt_tokens} "
                    f"completion={response.usage.completion_tokens} "
                    f"total={response.usage.total_tokens}"
                )

            return content

        except OpenAIRateLimitError as e:
            raise LLMRetryableError(f"Llama rate limit: {e}")
        except OpenAITimeoutError as e:
            raise LLMRetryableError(f"Llama timeout: {e}")
        except OpenAIConnectionError as e:
            raise LLMRetryableError(f"Llama connection error: {e}")
        except OpenAIAPIError as e:
            if hasattr(e, "status_code") and e.status_code and e.status_code >= 500:
                raise LLMRetryableError(f"Llama server error ({e.status_code}): {e}")
            raise LLMFatalError(f"Llama API error: {e}")

    async def close(self):
        """Release HTTP connection pool."""
        await self._client.close()


# ═══════════════════════════════════════════════════════
# CLAUDE CLIENT (Reflection Agent)
# ═══════════════════════════════════════════════════════

class ClaudeClient(BaseLLMClient):
    """
    Claude via Anthropic API.

    Used for final forensic verdict.
    Prompt-enforced JSON output.
    """

    def __init__(self):
        super().__init__(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=settings.CLAUDE_TEMPERATURE,
            timeout=settings.CLAUDE_TIMEOUT,
            max_retries=settings.MAX_RETRIES,
            retry_base_delay=settings.RETRY_BASE_DELAY,
        )
        self._client = AsyncAnthropic(
            api_key=settings.CLAUDE_API_KEY,
            timeout=float(self.timeout),
        )

    async def _raw_call(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
    ) -> str:
        """Call Claude via Anthropic API."""

        full_system = (
            f"{system_prompt}\n\n"
            f"RESPONSE FORMAT:\n"
            f"You MUST respond with valid JSON matching this exact schema:\n"
            f"{schema_hint}\n\n"
            f"Rules:\n"
            f"- Output ONLY the JSON object\n"
            f"- No markdown wrapping\n"
            f"- No extra text before or after\n"
            f"- All required fields must be present\n"
            f"- Enums must match exactly\n"
            f"- Do NOT include internal reasoning or chain-of-thought"
        )

        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=full_system,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )

            # Extract text blocks only
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            if not content.strip():
                raise LLMRetryableError("Empty response from Claude")

            # Log usage (no sensitive data)
            if response.usage:
                logger.debug(
                    f"Claude usage: "
                    f"input={response.usage.input_tokens} "
                    f"output={response.usage.output_tokens}"
                )

            return content

        except AnthropicRateLimitError as e:
            raise LLMRetryableError(f"Claude rate limit: {e}")
        except AnthropicTimeoutError as e:
            raise LLMRetryableError(f"Claude timeout: {e}")
        except AnthropicConnectionError as e:
            raise LLMRetryableError(f"Claude connection error: {e}")
        except AnthropicAPIError as e:
            if hasattr(e, "status_code") and e.status_code and e.status_code >= 500:
                raise LLMRetryableError(
                    f"Claude server error ({e.status_code}): {e}"
                )
            raise LLMFatalError(f"Claude API error: {e}")

    async def close(self):
        """Release HTTP connection pool."""
        await self._client.close()


# ═══════════════════════════════════════════════════════
# CLIENT FACTORY (Singleton)
# ═══════════════════════════════════════════════════════

_critic_client: Optional[LlamaClient] = None
_reflection_client: Optional[ClaudeClient] = None


def get_critic_client() -> LlamaClient:
    """Get or create singleton Llama client for Critic agent."""
    global _critic_client
    if _critic_client is None:
        _critic_client = LlamaClient()
        logger.info(f"Critic client initialized: {settings.LLAMA_MODEL}")
    return _critic_client


def get_reflection_client() -> ClaudeClient:
    """Get or create singleton Claude client for Reflection agent."""
    global _reflection_client
    if _reflection_client is None:
        _reflection_client = ClaudeClient()
        logger.info(f"Reflection client initialized: {settings.CLAUDE_MODEL}")
    return _reflection_client


async def shutdown_clients() -> None:
    """
    Gracefully close all LLM clients.
    Call this on FastAPI shutdown event.
    """
    global _critic_client, _reflection_client

    if _critic_client is not None:
        await _critic_client.close()
        _critic_client = None
        logger.info("Critic client closed")

    if _reflection_client is not None:
        await _reflection_client.close()
        _reflection_client = None
        logger.info("Reflection client closed")
