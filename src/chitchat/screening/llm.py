"""Structured LLM calls through mmore's LLM factory.

No outcome here stops a run: each call returns a status.
Retries for 429 and 5xx come from the LangChain client itself.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from chitchat.config import ConfigError, LLMSettings

log = logging.getLogger(__name__)

ERROR_CHARS = 500


def check_llm_reachable(settings: LLMSettings, timeout: float = 3.0) -> None:
    """For a model server at `base_url` (Ollama, vLLM): is it up, and is the model there?

    Raises ConfigError with a plain message. Hosted providers without base_url are not checked.
    """
    if not settings.base_url:
        return
    import httpx

    url = settings.base_url.rstrip("/") + "/models"
    local = any(h in settings.base_url for h in ("localhost", "127.0.0.1", "0.0.0.0"))
    hint = (
        " Is Ollama running? Start the Ollama app (or `ollama serve`)."
        if "11434" in settings.base_url
        else " Is the model server running?"
    )
    try:
        headers = {}
        if settings.provider:
            import os

            key = os.environ.get(f"{settings.provider.upper()}_API_KEY")
            if key:
                headers["Authorization"] = f"Bearer {key}"
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as e:
        if not local and isinstance(e, httpx.HTTPStatusError):
            return  # some hosted servers don't list models; let the real call decide
        raise ConfigError(f"Can't reach the model server at {settings.base_url}.{hint}") from None
    try:
        names = {m.get("id") for m in response.json().get("data", [])}
    except ValueError:
        return
    if names and settings.llm_name not in names:
        pull = f" Run: ollama pull {settings.llm_name}" if "11434" in settings.base_url else ""
        available = ", ".join(sorted(n for n in names if n)[:8])
        raise ConfigError(
            f"Model `{settings.llm_name}` isn't available at {settings.base_url}.{pull} "
            f"Available: {available or 'none'}."
        )


def build_chat_model(settings: LLMSettings) -> tuple[Any, str]:
    """Return (LangChain chat model, provider). Refuse local HF pipelines."""
    from mmore.rag.llm import LLM, LLMConfig

    check_llm_reachable(settings)

    config = LLMConfig(**settings.to_mmore())
    if config.provider == "HF":
        raise ConfigError(
            f"Model {settings.llm_name!r} would run as a local Hugging Face pipeline. "
            "Screening needs an API model or an OpenAI-compatible server (set base_url). "
            "For an API model mmore doesn't list, set `provider:`."
        )
    return LLM.from_config(config), config.provider or "OPENAI_COMPATIBLE"


class FatalLLMError(RuntimeError):
    """An error that would fail every paper, such as a bad API key. Stops the run."""


# Exception class names that mean every call will fail.
_FATAL_ERRORS = ("AuthenticationError", "PermissionDeniedError", "NotFoundError")


@dataclass
class CallResult:
    status: str  # ok | refused | invalid | error
    parsed: BaseModel | None = None
    error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


def _short(text: str) -> str:
    return text if len(text) <= ERROR_CHARS else text[: ERROR_CHARS - 1] + "…"


def _usage(raw: Any) -> dict[str, int]:
    meta = getattr(raw, "usage_metadata", None) or {}
    return {
        "input_tokens": int(meta.get("input_tokens", 0)),
        "output_tokens": int(meta.get("output_tokens", 0)),
    }


def _small_context(e: Exception) -> int | None:
    """The context size, when a reply was cut because a small context window filled up.

    Ollama's default window is 4096 tokens. A cut at 8192 or fewer means every
    long prompt will fail the same way, so the run should stop and say why.
    """
    if type(e).__name__ != "LengthFinishReasonError":
        return None
    usage = getattr(e, "completion", None)
    usage = getattr(usage, "usage", None)
    total = getattr(usage, "total_tokens", None)
    if total is None:
        match = re.search(r"total_tokens=(\d+)", str(e))
        total = int(match.group(1)) if match else None
    return total if total is not None and total <= 8192 else None


def _refusal(raw: Any) -> str | None:
    if raw is None:
        return None
    kwargs = getattr(raw, "additional_kwargs", None) or {}
    return kwargs.get("refusal") or getattr(raw, "refusal", None)


class StructuredCaller:
    """Calls a chat model with a Pydantic schema and classifies the outcome."""

    def __init__(
        self, chat_model: Any, schema: type[BaseModel], method: str = "json_schema"
    ) -> None:
        self.chat_model = chat_model
        self.schema = schema
        self.method = method
        self._structured = self._wrap()
        self._lock = threading.Lock()
        self._dropped_temperature = False

    def _wrap(self) -> Any:
        if self.method == "json_schema":  # the client's default; fakes in tests don't take `method`
            return self.chat_model.with_structured_output(self.schema, include_raw=True)
        return self.chat_model.with_structured_output(
            self.schema, include_raw=True, method=self.method
        )

    def _drop_temperature(self) -> bool:
        """Some reasoning models reject temperature. Drop it once, then retry."""
        with self._lock:
            if self._dropped_temperature:
                return True
            if not hasattr(self.chat_model, "temperature"):
                return False
            log.info("The model rejected `temperature`. Retrying without it.")
            self.chat_model.temperature = None
            self._structured = self._wrap()
            self._dropped_temperature = True
            return True

    def _with_schema(self, messages: list[Any]) -> list[Any]:
        """json_mode asks only for JSON, not for this schema, so put the schema in the prompt."""
        if self.method != "json_mode":
            return messages
        import json

        from langchain_core.messages import SystemMessage

        schema = json.dumps(self.schema.model_json_schema())
        hint = "Reply with one JSON object that matches this JSON schema:\n" + schema
        return [*messages, SystemMessage(content=hint)]

    def _invoke(self, messages: list[Any]) -> dict[str, Any]:
        messages = self._with_schema(messages)
        try:
            return self._structured.invoke(messages)
        except Exception as e:
            if "temperature" in str(e).lower() and self._drop_temperature():
                return self._structured.invoke(messages)
            raise

    def __call__(self, messages: list[Any]) -> CallResult:
        try:
            out = self._invoke(messages)
        except Exception as e:
            name = type(e).__name__
            if name in _FATAL_ERRORS:
                raise FatalLLMError(
                    f"The LLM provider refused the request ({name}). "
                    "Check the API key and the model name."
                ) from None
            window = _small_context(e)
            if window:
                raise FatalLLMError(
                    f"The model ran out of room: its context window is {window} tokens. "
                    "For Ollama, set OLLAMA_CONTEXT_LENGTH to 16384, then quit Ollama and "
                    "open it again (see docs/MODELS.md)."
                ) from None
            return CallResult("error", error=_short(f"{name}: {e}"))

        raw = out.get("raw")
        usage = _usage(raw)
        if out.get("parsed") is not None:
            return CallResult("ok", parsed=out["parsed"], usage=usage)
        refusal = _refusal(raw)
        if refusal:
            return CallResult("refused", error=_short(str(refusal)), usage=usage)
        error = out.get("parsing_error")
        return CallResult(
            "invalid", error=_short(str(error) if error else "no parsed output"), usage=usage
        )
