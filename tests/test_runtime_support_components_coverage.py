from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from src.api import progress_tracker as pt
from src.api import websocket_handler as ws
from src.core.orchestration import dynamic_scheduler as ds


def test_progress_tracker_and_aggregator_end_to_end() -> None:
    tracker = pt.ProgressTracker()
    events = []
    tracker.add_listener(events.append)

    task_id = tracker.create_task("demo", task_id="t1")
    assert task_id == "t1"
    assert tracker.start_task("t1") is True
    assert tracker.update_progress("t1", 0.5, "half", {"step": 1}) is True
    assert tracker.get_task_progress("t1").estimated_time_remaining is not None
    assert tracker.complete_task("t1", "done") is True
    assert tracker.get_active_tasks() == []

    failed_id = tracker.create_task("bad", task_id="t2")
    tracker.start_task(failed_id)
    assert tracker.fail_task(failed_id, "boom", {"code": 500}) is True
    assert tracker.cancel_task("missing") is False
    assert tracker.remove_listener(events.append) is True
    assert tracker.remove_listener(events[0].__class__) is False

    parent = tracker.create_task("parent", task_id="parent")
    tracker.start_task(parent)
    agg = pt.ProgressAggregator(tracker, parent)
    agg.add_sub_task("sub1", weight=1.0)
    agg.add_sub_task("sub2", weight=3.0)
    tracker.tasks["sub2"] = pt.TaskProgress("sub2", "sub2", pt.ProgressStatus.RUNNING, 0.5, 0.0, 0.0)
    agg.update_sub_task_progress("sub1", 1.0)
    assert tracker.get_task_progress(parent).progress > 0

    # global helpers
    original = pt._global_progress_tracker
    try:
        pt._global_progress_tracker = pt.ProgressTracker()
        tid = pt.create_task("global-task", "g1")
        assert pt.start_task(tid) is True
        assert pt.update_progress(tid, 0.2, "go") is True
        assert pt.complete_task(tid) is True
        assert pt.get_task_progress(tid).status == pt.ProgressStatus.COMPLETED
    finally:
        pt._global_progress_tracker = original


class _DummyWebSocket:
    def __init__(self, messages=None):
        self.closed = False
        self.sent = []
        self.remote_address = ("127.0.0.1", 9000)
        self._messages = list(messages or [])

    async def send(self, payload):
        self.sent.append(payload)

    def __aiter__(self):
        self._iter = iter(self._messages)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def test_websocket_manager_and_notifier(monkeypatch) -> None:
    manager = ws.WebSocketManager()
    monkeypatch.setattr(ws, "WEBSOCKETS_AVAILABLE", False)
    assert manager.broadcast_message("progress", {"ok": 1}) == 0

    monkeypatch.setattr(ws, "WEBSOCKETS_AVAILABLE", True)
    class _Loop:
        def is_running(self):
            return False

        def run_until_complete(self, coro):
            return asyncio.run(coro)

    monkeypatch.setattr(ws.asyncio, "get_event_loop", lambda: _Loop())
    conn = _DummyWebSocket()
    manager.add_connection("progress", conn)
    sent = manager.broadcast_message("progress", {"kind": "test"})
    assert sent == 1
    assert json.loads(conn.sent[0])["kind"] == "test"

    pong = manager._handle_client_message("progress", {"type": "ping"})
    assert pong["type"] == "pong"
    unknown = manager._handle_client_message("progress", {"type": "x"})
    assert unknown["type"] == "unknown_message_type"

    notifier = ws.ProgressWebSocketNotifier(manager)
    called = []
    notifier.add_notification_handler(lambda task_id, progress_data, message: called.append((task_id, message["type"])))
    total = notifier.notify_progress_update("t1", {"progress": 0.3})
    assert total >= 0
    assert called and called[0][1] == "progress_update"
    assert notifier.notify_task_status("t1", "done", "ok") >= 0
    assert notifier.remove_notification_handler(called.append) is False


@pytest.mark.asyncio
async def test_websocket_handle_client_and_server_helpers(monkeypatch) -> None:
    manager = ws.WebSocketManager()
    websocket = _DummyWebSocket(messages=['{"type":"ping"}', 'not-json'])

    async def fake_serve(handler, host, port):
        return SimpleNamespace(wait_closed=lambda: asyncio.sleep(0), close=lambda: None)

    monkeypatch.setattr(ws, "WEBSOCKETS_AVAILABLE", True)
    monkeypatch.setattr(ws, "websockets", SimpleNamespace(serve=fake_serve, exceptions=SimpleNamespace(ConnectionClosed=RuntimeError)))
    await manager.handle_client(websocket, "/progress/demo")
    assert any("welcome" in item for item in websocket.sent)
    assert any("pong" in item for item in websocket.sent)
    assert any("无效的JSON格式" in item for item in websocket.sent)

    # global helpers
    ws._global_ws_manager = None
    ws._global_notifier = None
    assert ws.get_websocket_manager() is not None
    assert ws.get_progress_notifier() is not None
    monkeypatch.setattr(ws, "WEBSOCKETS_AVAILABLE", False)
    assert ws.start_websocket_server(9999) is False
    ws.stop_websocket_server()


class _Monitor:
    def __init__(self):
        self.started = False

    def start_monitoring(self, interval):
        self.started = True

    def stop_monitoring(self):
        self.started = False

    def get_resource_pressure(self):
        return {"cpu": 0.1, "memory": 0.2, "disk": 0.1}

    def get_system_health(self):
        return {"cpu": "good", "memory": "good", "disk": "good"}


class _ThreadStub:
    def __init__(self, target=None, args=(), daemon=None):
        self.target = target
        self.args = args

    def start(self):
        return None

    def join(self, timeout=None):
        return None


def test_dynamic_scheduler_core_paths(monkeypatch) -> None:
    monitor = _Monitor()
    monkeypatch.setattr(ds, "get_system_monitor", lambda: monitor)
    monkeypatch.setattr(ds.threading, "Thread", _ThreadStub)

    scheduler = ds.DynamicScheduler(max_workers=4, min_workers=1, adaptation_interval=0.01)
    scheduler.start()
    assert scheduler.running is True and monitor.started is True

    monkeypatch.setattr(scheduler, "_check_resource_availability", lambda task: True)
    started = []
    monkeypatch.setattr(scheduler, "_start_task", lambda task: started.append(task.task_id))
    scheduler.submit_task(lambda: None, "task-high", priority=ds.TaskPriority.HIGH)
    scheduler.submit_task(lambda: None, "task-low", priority=ds.TaskPriority.LOW)
    assert started[0] == "task-high"

    pressure = {"cpu": 0.2, "memory": 0.3, "disk": 0.1}
    health = {"cpu": "good", "memory": "critical", "disk": "good"}
    target = scheduler._calculate_target_workers(pressure, health)
    assert scheduler.min_workers <= target <= scheduler.max_workers
    scheduler._adapt_worker_count()
    status = scheduler.get_status()
    assert "resource_pressure" in status
    assert isinstance(scheduler.get_active_tasks(), list)

    scheduler.active_tasks["running"] = ds.TaskInfo(
        task_id="running",
        priority=ds.TaskPriority.NORMAL,
        resource_requirements={"cpu": 0.1},
        estimated_duration=1.0,
        created_at=0.0,
        started_at=0.0,
        status="running",
    )
    assert scheduler.get_active_tasks()[0]["task_id"] == "running"

    scheduler.active_tasks.clear()
    scheduler.stop()
    assert scheduler.running is False

    original = ds._global_scheduler
    try:
        ds._global_scheduler = None
        monkeypatch.setattr(ds, "get_system_monitor", lambda: _Monitor())
        monkeypatch.setattr(ds.threading, "Thread", _ThreadStub)
        s = ds.get_scheduler()
        monkeypatch.setattr(s, "submit_task", lambda task_func, task_id, **kwargs: f"submitted:{task_id}")
        assert ds.submit_task(lambda: None, "g-task") == "submitted:g-task"
        assert isinstance(ds.get_scheduler_status(), dict)
    finally:
        ds._global_scheduler = original
