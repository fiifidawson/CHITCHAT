"""Structured LLM calls through mmore's LLM factory.

No outcome here stops a run: each call returns a status.
Retries for 429 and 5xx come from the LangChain client itself.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from chitchat.config import ConfigError, LLMSettings

log = logging.getLogger(__name__)

ERROR_CHARS = 500


def build_chat_model(settings: LLMSettings) -> tuple[Any, str]:
    """Return (LangChain chat model, provider). Refuse local HF pipelines."""
    from mmore.rag.llm import LLM, LLMConfig

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


def _refusal(raw: Any) -> str | None:
    if raw is None:
        return None
    kwargs = getattr(raw, "additional_kwargs", None) or {}
    return kwargs.get("refusal") or getattr(raw, "refusal", None)


class StructuredCaller:
    """Calls a chat model with a Pydantic schema and classifies the outcome."""

    def __init__(self, chat_model: Any, schema: type[BaseModel]) -> None:
        self.chat_model = chat_model
        self.schema = schema
        self._structured = chat_model.with_structured_output(schema, include_raw=True)
        self._lock = threading.Lock()
        self._dropped_temperature = False

    def _drop_temperature(self) -> bool:
        """Some reasoning models reject temperature. Drop it once, then retry."""
        with self._lock:
            if self._dropped_temperature:
                return True
            if not hasattr(self.chat_model, "temperature"):
                return False
            log.info("The model rejected `temperature`. Retrying without it.")
            self.chat_model.temperature = None
            self._structured = self.chat_model.with_structured_output(self.schema, include_raw=True)
            self._dropped_temperature = True
            return True

    def _invoke(self, messages: list[Any]) -> dict[str, Any]:
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
