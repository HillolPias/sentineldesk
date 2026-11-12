import asyncio
import sys

from worker.pipeline import setup_checkpointer


def _capture_run(monkeypatch):
    calls = []

    def fake_run(coro, **kwargs):
        calls.append(kwargs)
        coro.close()  # we only care how it was started, not that it runs

    monkeypatch.setattr(asyncio, "run", fake_run)
    return calls


def test_main_actually_runs_setup_on_linux(monkeypatch):
    calls = _capture_run(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")

    setup_checkpointer.main()

    assert calls == [{}]


def test_main_uses_selector_loop_on_windows(monkeypatch):
    calls = _capture_run(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")

    setup_checkpointer.main()

    assert calls == [{"loop_factory": asyncio.SelectorEventLoop}]
