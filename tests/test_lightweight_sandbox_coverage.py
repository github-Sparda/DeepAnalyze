from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import src.core.security.lightweight_sandbox as sandbox_mod


class _FakeProcess:
    def __init__(self, *, stdout="ok", stderr="", returncode=0, pid=123, timeout=False):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.pid = pid
        self._timeout = timeout
        self._start_time = "start"
        self.terminated = False
        self.killed = False

    def communicate(self, timeout=None):
        if self._timeout:
            raise subprocess.TimeoutExpired("cmd", timeout)
        return self._stdout, self._stderr

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if self._timeout and timeout == 5:
            raise subprocess.TimeoutExpired("cmd", timeout)
        return self.returncode

    def kill(self):
        self.killed = True

    def poll(self):
        return None


def test_lightweight_sandbox_execute_success_timeout_and_exception(monkeypatch, tmp_path: Path):
    sandbox = sandbox_mod.LightweightSandbox()
    monkeypatch.setattr(sandbox, "_get_memory_usage", lambda pid: 2048)

    created = []
    def _named_tempfile(*args, **kwargs):
        path = tmp_path / f"code_{len(created)}.py"
        created.append(path)
        class _Ctx:
            name = str(path)
            def __enter__(self_nonlocal):
                self_nonlocal.handle = path.open("w", encoding="utf-8")
                return self_nonlocal.handle
            def __exit__(self_nonlocal, *exc):
                self_nonlocal.handle.close()
        return _Ctx()
    monkeypatch.setattr(sandbox_mod.tempfile, "NamedTemporaryFile", _named_tempfile)
    monkeypatch.setattr(sandbox_mod.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    result = sandbox.execute_code("print(1)", user_id="u1", timeout=1)
    assert result.success is True
    assert result.memory_used == 2048

    monkeypatch.setattr(sandbox_mod.subprocess, "Popen", lambda *a, **k: _FakeProcess(timeout=True))
    timeout_result = sandbox.execute_code("print(1)", user_id="u2", timeout=1)
    assert timeout_result.error_message == "timeout"

    monkeypatch.setattr(sandbox_mod.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("popen bad")))
    error_result = sandbox.execute_code("print(1)", user_id="u3")
    assert error_result.success is False


def test_lightweight_sandbox_helpers_and_restricted_env(monkeypatch, tmp_path: Path):
    sandbox = sandbox_mod.LightweightSandbox()
    assert sandbox._build_restricted_command("/tmp/x.py") == ["nice", "-n", "19", "python3", "/tmp/x.py"]

    limits_called = []
    monkeypatch.setattr(sandbox_mod.resource, "setrlimit", lambda *args: limits_called.append(args))
    monkeypatch.setattr(sandbox_mod.tempfile, "mkdtemp", lambda: str(tmp_path))
    monkeypatch.setattr(sandbox_mod.os, "chdir", lambda path: None)
    sandbox._create_preexec_function()()
    assert limits_called

    proc = _FakeProcess()
    sandbox.active_processes["u1"] = proc
    assert sandbox.get_active_processes()["u1"]["status"] == "running"
    sandbox._terminate_process("u1")
    assert "u1" not in sandbox.active_processes

    sandbox.active_processes["u2"] = _FakeProcess(timeout=True)
    sandbox.active_processes["u3"] = _FakeProcess()
    sandbox.terminate_all_processes()
    assert sandbox.active_processes == {}

    env = sandbox_mod.RestrictedPythonEnvironment(sandbox)
    wrapped = env._wrap_code_with_restrictions("print('x')")
    assert "dangerous_functions" in wrapped
    assert env._indent_code("a\nb", 2) == "  a\n  b"
    monkeypatch.setattr(sandbox, "execute_code", lambda code, user_id="default", timeout=None: sandbox_mod.ExecutionResult(True, code, "", 0, 0.1))
    safe_result = env.execute_safe_code("print(1)", user_id="u4")
    assert safe_result.success is True

    sandbox_mod._global_sandbox = sandbox
    sandbox_mod._global_restricted_env = env
    assert sandbox_mod.execute_in_sandbox("print(1)").success is True
    assert sandbox_mod.get_sandbox_stats()["active_processes"] == 0
    sandbox_mod._global_sandbox = None
    sandbox_mod._global_restricted_env = None

