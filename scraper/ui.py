"""
Minimal terminal UI helpers — ANSI colours + a tiny progress bar.

Used only when the user passes --ui on the CLI. Falls back to plain
text automatically when:

  * stdout is not a TTY (e.g. output is redirected to a file)
  * the NO_COLOR environment variable is set (https://no-color.org/)
  * the user explicitly passes ui_enabled=False at construction

This module has zero third-party dependencies — it uses only the
Python standard library.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Optional, TextIO


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
# Conservative 8-colour palette. Foreground only, no background.
_RESET = "\033[0m"
_COLOURS = {
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "grey":    "\033[90m",
    "bold":    "\033[1m",
}


def _should_colour(stream: TextIO) -> bool:
    """Decide whether ANSI escape codes should be emitted on `stream`."""
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    try:
        return stream.isatty()
    except Exception:
        return False


def colour(text: str, name: str, enabled: bool = True) -> str:
    """Wrap `text` in ANSI colour codes iff `enabled` is True."""
    if not enabled:
        return text
    code = _COLOURS.get(name, "")
    if not code:
        return text
    return f"{code}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------
@dataclass
class ProgressBar:
    """Minimal in-place progress bar: "[██████░░░░]  60%  (3/5)".

    Renders to `stream` (default sys.stderr so it doesn't interfere with
    a piped stdout). Updates in place using "\r" + ANSI line-clear so a
    slow terminal doesn't accumulate stale frames.

    When `enabled` is False every method is a no-op — callers can
    unconditionally invoke update()/finish() without checking.
    """
    total: int
    label: str = ""
    width: int = 20
    enabled: bool = True
    stream: TextIO = field(default_factory=lambda: sys.stderr)
    coloured: bool = field(init=False)
    _done: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.coloured = self.enabled and _should_colour(self.stream)
        self._done = 0
        if self.total < 1:
            self.total = 1   # avoid div-by-zero
        self._render()

    def update(self, n: int = 1, suffix: str = "") -> None:
        """Advance the bar by `n` steps and re-render."""
        if not self.enabled:
            return
        self._done = min(self.total, self._done + n)
        self._render(suffix)

    def set(self, value: int, suffix: str = "") -> None:
        """Set the bar to an absolute value."""
        if not self.enabled:
            return
        self._done = max(0, min(self.total, value))
        self._render(suffix)

    def finish(self, suffix: str = "") -> None:
        """Snap to 100% and emit a final newline so subsequent output
        doesn't overwrite the bar."""
        if not self.enabled:
            return
        self._done = self.total
        self._render(suffix)
        self.stream.write("\n")
        self.stream.flush()

    def _render(self, suffix: str = "") -> None:
        if not self.enabled:
            return
        pct = int(self._done * 100 / self.total)
        filled = int(self.width * self._done / self.total)
        bar = "█" * filled + "░" * (self.width - filled)
        pct_str = f"{pct:3d}%"
        counter = f"({self._done}/{self.total})"
        # Cyan bar, grey counter, white label.
        line_parts = [
            colour(f"[{bar}]", "cyan", self.coloured),
            colour(f" {pct_str} ", "bold", self.coloured),
            colour(counter, "grey", self.coloured),
        ]
        if self.label:
            line_parts.insert(0, colour(self.label + " ", "bold", self.coloured))
        if suffix:
            line_parts.append(" " + colour(suffix, "white", self.coloured))
        # "\033[2K" clears the entire current line so a shrinking suffix
        # doesn't leave ghost characters behind. It is a CSI escape but
        # it does NOT introduce colour — emit it even when colours are
        # disabled, otherwise the bar will smear across lines.
        self.stream.write("\033[2K\r" + "".join(line_parts))
        self.stream.flush()


# ---------------------------------------------------------------------------
# Console wrapper
# ---------------------------------------------------------------------------
class _NoopProgress:
    """Stand-in ProgressBar used when --ui is OFF."""
    def update(self, n: int = 1, suffix: str = "") -> None: pass
    def set(self, value: int, suffix: str = "") -> None: pass
    def finish(self, suffix: str = "") -> None: pass


class Console:
    """Convenience facade: holds the colour flag and a ProgressBar."""

    def __init__(self, enabled: bool = True, stream: TextIO = sys.stdout):
        self.enabled = enabled
        self.stream = stream
        self.coloured = enabled and _should_colour(stream)

    # ---- coloured output (no-op when disabled) ----
    def print(self, text: str, colour_name: Optional[str] = None) -> None:
        if not self.enabled:
            return
        if colour_name:
            self.stream.write(colour(text, colour_name, self.coloured) + "\n")
        else:
            self.stream.write(text + "\n")
        self.stream.flush()

    def info(self, text: str)  -> None:
        if self.enabled: self.print(text, "cyan")
    def ok(self, text: str)    -> None:
        if self.enabled: self.print(text, "green")
    def warn(self, text: str)  -> None:
        if self.enabled: self.print(text, "yellow")
    def err(self, text: str)   -> None:
        if self.enabled: self.print(text, "red")
    def header(self, text: str)-> None:
        if not self.enabled:
            return
        bar = "═" * max(0, 60 - len(text) - 2)
        self.print(f"══ {text} {bar}", "blue")

    # ---- progress ----
    def progress(self, total: int, label: str = "") -> ProgressBar:
        """Return a ProgressBar (or a no-op if UI is disabled)."""
        if not self.enabled:
            return _NoopProgress()  # type: ignore[return-value]
        return ProgressBar(total=total, label=label,
                           enabled=True, stream=sys.stderr)


# Module-level default — overwritten by main.py if --ui is passed.
console = Console(enabled=False)