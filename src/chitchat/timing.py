"""Run timing, run history and per-run log files.

Every command that runs stages is one *run*, with an id like `2026-10-21T14-03-07`.
It is appended to `runs/<run>/history.jsonl`, and its terminal output is saved
to `runs/<run>/logs/<run id>.log`, even when a stage fails.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from chitchat.jsonl import append_jsonl
from chitchat.run_dir import RunDir


def format_duration(seconds: float) -> str:
    """`4.2s`, `3m 12s` or `1h 05m`."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _now() -> datetime:
    return datetime.now().astimezone()


class RunRecorder:
    """Times the stages of one run and records it when the run ends.

    Use as a context manager. The outcome is `done`, `failed` or `interrupted`.
    """

    def __init__(
        self, run: RunDir, command: str, config: Path | str, mode: str | None = None
    ) -> None:
        self.run = run
        self.command = command
        self.config = str(config)
        self.mode = mode
        self.started = _now()
        self.run_id = self.started.strftime("%Y-%m-%dT%H-%M-%S")
        self.stages: list[dict[str, Any]] = []
        self.error: str | None = None
        self.outcome: str | None = None
        self._t0 = time.perf_counter()
        self.seconds = 0.0

    @property
    def log_path(self) -> Path:
        return self.run.logs / f"{self.run_id}.log"

    @contextmanager
    def stage(self, name: str) -> Iterator[dict[str, Any]]:
        """Times one stage. A stage that raises is recorded as failed."""
        entry: dict[str, Any] = {"name": name, "started": _now().isoformat(timespec="seconds")}
        t0 = time.perf_counter()
        try:
            yield entry
            entry["status"] = "done"
        except KeyboardInterrupt:
            entry["status"] = "interrupted"
            raise
        except BaseException as e:
            entry["status"] = "failed"
            entry["error"] = str(e)[:500]
            raise
        finally:
            entry["seconds"] = round(time.perf_counter() - t0, 2)
            self.stages.append(entry)

    def fail(self, error: str) -> None:
        self.error = error[:500]

    def __enter__(self) -> RunRecorder:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.seconds = round(time.perf_counter() - self._t0, 2)
        if self.error:
            self.outcome = "failed"
        elif exc_type is KeyboardInterrupt:
            self.outcome = "interrupted"
        elif exc_type is not None and not _is_clean_exit(exc):
            self.outcome = "failed"
            self.error = f"{exc_type.__name__}: {exc}"[:500]
        else:
            self.outcome = "done"
        self._write_history()
        self._write_log()

    def record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "command": self.command,
            "config": self.config,
            "mode": self.mode,
            "started": self.started.isoformat(timespec="seconds"),
            "ended": _now().isoformat(timespec="seconds"),
            "seconds": self.seconds,
            "outcome": self.outcome,
            "error": self.error,
            "stages": self.stages,
        }

    def _write_history(self) -> None:
        self.run.root.mkdir(parents=True, exist_ok=True)
        append_jsonl(self.run.history, self.record())

    def _write_log(self) -> None:
        from chitchat import ui

        header = [
            f"chitchat {self.command}",
            f"run id:   {self.run_id}",
            f"config:   {self.config}",
            f"mode:     {self.mode or '-'}",
            f"started:  {self.started.isoformat(timespec='seconds')}",
            f"outcome:  {self.outcome} after {format_duration(self.seconds)}",
            "-" * 72,
            "",
        ]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        text = ui.console.export_text(clear=False) if ui.console.record else ""
        self.log_path.write_text("\n".join(header) + text, encoding="utf-8")


def _is_clean_exit(exc: BaseException | None) -> bool:
    """typer/click exits with code 0 are not failures."""
    code = getattr(exc, "exit_code", getattr(exc, "code", None))
    return code in (0, None) and type(exc).__name__ in ("Exit", "SystemExit")
