import os
import signal
import subprocess
import sys

import pytest

from pyhub.mcptools.core.sidecar import Sidecar

# --- 공통 Fixture 및 DummyProc 정의 (생략) ---


@pytest.fixture(autouse=True)
def restore_os_name():
    orig = os.name
    yield
    os.name = orig


# Windows 전용: Windows가 아닐 때 스킵
@pytest.mark.skipif(sys.platform != "win32", reason="Windows에서만 실행")
def test_windows_branch(monkeypatch):
    os.name = "nt"
    created = []

    class DummyProc:
        def __init__(self):
            self.signals = []

        def send_signal(self, sig):
            self.signals.append(sig)

        def kill(self):
            pass

        def wait(self, timeout):
            pass

        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        _proc = DummyProc()
        created.append((args, kwargs, _proc))
        return _proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    with Sidecar(["cmd1", "cmd2"]):
        for __, kwargs, __ in created:
            assert kwargs.get("creationflags") == subprocess.CREATE_NEW_PROCESS_GROUP
            assert "preexec_fn" not in kwargs

    for __, __, proc in created:
        assert signal.CTRL_BREAK_EVENT in proc.signals


@pytest.mark.skipif(sys.platform != "win32", reason="Windows에서만 실행")
def test_windows_kill_on_timeout(monkeypatch):
    os.name = "nt"
    called = {"send": False, "kill": False}

    class Proc:
        def __init__(self):
            self.signals = []

        def send_signal(self, sig):
            called["send"] = True
            raise Exception("Simulated send_signal failure")

        def kill(self):
            called["kill"] = True

        def wait(self, timeout):
            raise subprocess.TimeoutExpired("dummy", timeout)

        def poll(self):
            return None

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Proc())
    with Sidecar(["dummy"]):
        pass
    # send_signal 호출 여부와 kill 호출 여부를 모두 확인
    assert called["send"] is True
    assert called["kill"] is True


# POSIX 전용: POSIX가 아닐 때 스킵
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 환경에서만 실행")
def test_posix_multiple_processes(monkeypatch):
    os.name = "posix"
    procs = []

    class DummyProc:
        def __init__(self):
            self.wait_called = False

        def wait(self, timeout):
            self.wait_called = True
            raise subprocess.TimeoutExpired(cmd="dummy", timeout=timeout)

        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        proc = DummyProc()
        procs.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    with Sidecar(["sleep 1", "sleep 2", "sleep 3"]):
        assert len(procs) == 3
        for p in procs:
            assert p.poll() is None

    for p in procs:
        assert p.wait_called


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 환경에서만 실행")
def test_partial_start_failure(monkeypatch):
    os.name = "posix"
    calls = []

    class DummyProc:
        def __init__(self):
            self.wait_called = False

        def wait(self, timeout):
            self.wait_called = True
            raise subprocess.TimeoutExpired(cmd="dummy", timeout=timeout)

        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        if not calls:
            calls.append("fail")
            raise FileNotFoundError
        proc = DummyProc()
        calls.append("ok")
        return proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    with pytest.raises(FileNotFoundError):
        with Sidecar(["badcmd", "echo hi"]):
            pass
    assert calls == ["fail", "ok"]
