from __future__ import annotations

import queue
from types import SimpleNamespace

import pytest

import src.core.security.container_pool as container_pool


class _ExecResult:
    def __init__(self, exit_code=0, output=b"ok"):
        self.exit_code = exit_code
        self.output = output


class _FakeContainer:
    def __init__(self, name="c1", exec_result=None):
        self.name = name
        self._exec_result = exec_result or _ExecResult()
        self.commands = []
        self.stopped = False
        self.removed = False

    def start(self):
        return None

    def exec_run(self, cmd, stream=False, timeout=None, workdir=None):
        self.commands.append((cmd, stream, timeout, workdir))
        if isinstance(self._exec_result, Exception):
            raise self._exec_result
        return self._exec_result

    def stop(self, timeout=10):
        self.stopped = True

    def remove(self, force=True):
        self.removed = True


class _FakeDockerClient:
    def __init__(self, containers):
        self._containers = list(containers)
        self.api = SimpleNamespace(create_host_config=lambda **kwargs: kwargs)
        self.containers = SimpleNamespace(create=self._create)

    def ping(self):
        return True

    def _create(self, **kwargs):
        if not self._containers:
            raise RuntimeError("no container")
        return self._containers.pop(0)


class _AlwaysFullQueue:
    def put(self, item, timeout=None):
        raise queue.Full

    def qsize(self):
        return 0

    def empty(self):
        return True


def _build_pool(monkeypatch, containers, pool_size=2):
    monkeypatch.setattr(container_pool.docker, "from_env", lambda: _FakeDockerClient(containers))
    monkeypatch.setattr(container_pool.ContainerPool, "_start_monitoring", lambda self: setattr(self, "running", False))
    return container_pool.ContainerPool(pool_size=pool_size)


def test_container_pool_session_lifecycle_and_stats(monkeypatch):
    pool = _build_pool(monkeypatch, [_FakeContainer("c1"), _FakeContainer("c2")])
    session = pool.get_container("u1")
    assert session.user_id == "u1"
    same = pool.get_container("u1")
    assert same.session_id == session.session_id

    result = pool.execute_in_session("u1", "print(1)", timeout=5)
    assert result["success"] is True
    assert result["stdout"] == "ok"

    stats = pool.get_stats()
    assert stats.total_capacity == 2
    assert stats.active_sessions == 1

    pool.release_container("u1")
    assert stats.total_capacity == 2
    pool.shutdown()


def test_container_pool_errors_timeout_cleanup_and_globals(monkeypatch):
    pool = _build_pool(monkeypatch, [_FakeContainer("c1", exec_result=RuntimeError("bad")), _FakeContainer("c2")], pool_size=1)
    session = pool.get_container("u1")
    result = pool.execute_in_session("u1", "boom")
    assert result["success"] is False
    session.last_access = 0

    with pytest.raises(TimeoutError):
        pool.get_container("u2", timeout=0.001)

    released = []
    original_release = pool.release_container
    monkeypatch.setattr(pool, "release_container", lambda user_id: released.append(user_id))
    pool._cleanup_expired_sessions()
    assert released == ["u1"]
    monkeypatch.setattr(pool, "release_container", original_release)

    monkeypatch.setattr(pool, "_create_container", lambda: _FakeContainer("c3"))
    pool.busy_containers.clear()
    pool.user_sessions.clear()
    pool._maintain_pool_size()
    assert pool.available_containers.qsize() >= 1

    extra = _FakeContainer("extra")
    session2 = container_pool.ContainerSession(extra, "s2", "u2")
    pool.busy_containers["s2"] = session2
    pool.user_sessions["u2"] = "s2"
    pool.available_containers = _AlwaysFullQueue()
    pool.release_container("u2")
    assert extra.removed is True
    pool.available_containers = queue.Queue(maxsize=1)
    pool.available_containers.put(_FakeContainer("c4"))

    container_pool._global_container_pool = pool
    assert container_pool.execute_with_container("u3", "print(1)")["session_id"]
    pool_stats = container_pool.get_pool_stats()
    assert "available_count" in pool_stats
    container_pool._global_container_pool = None


def test_container_pool_init_failure(monkeypatch):
    monkeypatch.setattr(container_pool.docker, "from_env", lambda: (_ for _ in ()).throw(RuntimeError("no docker")))
    with pytest.raises(RuntimeError):
        container_pool.ContainerPool(pool_size=1)
