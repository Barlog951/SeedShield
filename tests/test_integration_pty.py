"""
End-to-end tests that drive the real curses UI through a pseudo-terminal.

Mock-based tests cannot see what the terminal actually receives: these caught
that hover never worked (ncurses only enables click reporting) and that a
click on the menu revealed a word that was not on screen.
"""

import os
import re
import subprocess
import sys
import time
from typing import Callable, List

import pytest

from seedshield.config import DEFAULT_WORDLIST_FULLPATH

pytestmark = [
    pytest.mark.skipif(sys.platform == "win32", reason="requires a POSIX pty"),
    pytest.mark.timeout(60),
]

ROWS, COLS = 30, 100
MENU_ROW = ROWS - 5  # "Commands:" row (0-based)

with open(DEFAULT_WORDLIST_FULLPATH, encoding="utf-8") as _f:
    WORDS: List[str] = _f.read().split()


class TerminalSession:
    """A running seedshield process attached to a pseudo-terminal."""

    def __init__(self) -> None:
        import pty  # pylint: disable=import-outside-toplevel

        self.master, slave = pty.openpty()
        env = dict(os.environ, TERM="xterm-256color", LINES=str(ROWS), COLUMNS=str(COLS))
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        self.proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, "-m", "seedshield.main"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=env,
            start_new_session=True,
        )
        os.close(slave)
        self.output = bytearray()
        self.closed = False

    def pump(self, seconds: float) -> None:
        """Collect output for a fixed time."""
        self.wait_for(lambda _: False, seconds)

    def wait_for(self, predicate: Callable[[str], bool], timeout: float = 10.0) -> bool:
        """Collect output until predicate(text) holds or the timeout expires."""
        import select  # pylint: disable=import-outside-toplevel

        deadline = time.time() + timeout
        eof = False
        while time.time() < deadline:
            if predicate(self.text()):
                return True
            if eof:
                # The pty can report EOF before the exited child is reaped,
                # so keep re-checking the predicate instead of giving up
                time.sleep(0.05)
                continue
            ready, _, _ = select.select([self.master], [], [], 0.05)
            if ready:
                try:
                    data = os.read(self.master, 65536)
                except OSError:
                    data = b""
                eof = not data
                self.output.extend(data)
        return predicate(self.text())

    def text(self, since: int = 0) -> str:
        return self.output[since:].decode("utf-8", "replace")

    def send(self, data: bytes) -> int:
        """Send input; returns the output offset from before the send."""
        mark = len(self.output)
        os.write(self.master, data)
        return mark

    def mouse(self, button: int, x: int, y: int) -> bytes:
        """Encode a mouse report in the protocol ncurses asked the terminal for."""
        if b"1006" in self.output:
            return f"\x1b[<{button};{x + 1};{y + 1}M".encode()
        return b"\x1b[M" + bytes([32 + button, 33 + x, 33 + y])

    def close(self) -> None:
        """Quit the app (from either screen) and collect its final output."""
        if self.closed:
            return
        self.closed = True
        try:
            os.write(self.master, b"q\r")
            # Keep draining while it exits: unread pty output is lost on macOS
            if not self.wait_for(lambda _: self.proc.poll() is not None, 10):
                self.proc.kill()
        except OSError:
            self.proc.kill()
        finally:
            self.proc.wait()
            os.close(self.master)


@pytest.fixture
def session():
    term = TerminalSession()
    assert term.wait_for(lambda t: "Enter position" in t), term.text()
    yield term
    term.close()


def _enter_positions(term: TerminalSession, positions: str) -> None:
    term.send(positions.encode() + b"\r")
    assert term.wait_for(lambda t: "Commands:" in t), term.text()


def _shows(text: str, word: str) -> bool:
    return re.search(rf"\b{word}\b", text) is not None


def test_typed_positions_reveal_correct_word(session):
    """Multi-position input and 's' reveal the word at the first position."""
    _enter_positions(session, "12 1")
    mark = session.send(b"s")
    assert session.wait_for(lambda _: _shows(session.text(mark), WORDS[11]))
    assert not _shows(session.text(mark), WORDS[0])


def test_slow_typing_is_not_truncated(session):
    """Pauses between keys (halfdelay mode) must not cut the number short."""
    for key in (b"1", b"2"):
        session.send(key)
        session.pump(0.3)
    _enter_positions(session, "")
    mark = session.send(b"s")
    assert session.wait_for(lambda _: _shows(session.text(mark), WORDS[11]))


def test_hover_tracking_enabled_and_restored(session):
    """Hover needs xterm mode 1003 on, and it must be switched off on exit."""
    assert b"\x1b[?1003h" in session.output
    session.close()
    assert b"\x1b[?1003l" in session.output


def test_hover_reveals_word_under_pointer(session):
    """Moving the pointer over a word row reveals it."""
    _enter_positions(session, "1 2 3")
    mark = session.send(session.mouse(35, 5, 0))  # motion, no button
    assert session.wait_for(lambda _: _shows(session.text(mark), WORDS[0]))


def test_click_on_menu_reveals_nothing(session):
    """Regression: a click below the drawn rows revealed an off-screen word."""
    _enter_positions(session, " ".join(str(i) for i in range(1, 21)))
    mark = session.send(session.mouse(0, 5, MENU_ROW))
    session.pump(1.0)
    leaked = [w for w in WORDS[:20] if _shows(session.text(mark), w)]
    assert leaked == []


def _active_mouse_modes(data: bytes) -> set:
    """Replay xterm private-mode switches and return the mouse modes left on."""
    active = set()
    for modes, action in re.findall(rb"\x1b\[\?([0-9;]+)([hl])", data):
        for mode in modes.split(b";"):
            if mode in (b"1000", b"1002", b"1003", b"1006"):
                (active.add if action == b"h" else active.discard)(mode)
    return active


def test_mouse_reporting_off_while_typing(session):
    """Regression: getstr() beeped on every hover report while positions were typed."""
    session.pump(0.3)
    assert not _active_mouse_modes(bytes(session.output)) & {b"1000", b"1003"}

    _enter_positions(session, "1 2")
    assert {b"1000", b"1003"} <= _active_mouse_modes(bytes(session.output))

    # Back to the input screen via 'n': reporting is switched off again
    session.send(b"n")
    assert session.wait_for(lambda t: t.rfind("Enter position") > t.rfind("Commands:"))
    session.pump(0.3)
    assert not _active_mouse_modes(bytes(session.output)) & {b"1000", b"1003"}


def test_sigterm_restores_terminal(session):
    """A killed process must still wipe the screen and switch hover tracking off."""
    import signal  # pylint: disable=import-outside-toplevel

    _enter_positions(session, "1 2")
    assert b"\x1b[?1003h" in session.output
    mark = len(session.output)
    session.proc.send_signal(signal.SIGTERM)
    assert session.wait_for(lambda _: session.proc.poll() is not None)
    assert b"\x1b[?1003l" in session.output[mark:]
    assert session.proc.returncode == 143
