"""
Test: Task Queue Abstraction (Phase 2)
=======================================
Tests the in-memory task queue for enqueue/dequeue/status operations
and the worker's task routing logic.
"""
import pytest
from app.services.ingestion.task_queue import (
    InMemoryTaskQueue,
    TaskPayload,
    TaskStatus,
    create_task,
    get_task_queue,
)


class TestTaskQueue:
    def test_enqueue_dequeue_cycle(self):
        """Enqueue a task, dequeue it, verify payload matches."""
        q = InMemoryTaskQueue()
        task = TaskPayload(
            task_id="test-001",
            task_type="document_processing",
            payload={"document_id": "doc-abc123"}
        )
        tid = q.enqueue(task)
        assert tid == "test-001"
        assert q.get_queue_length() == 1

        dequeued = q.dequeue(timeout=1)
        assert dequeued is not None
        assert dequeued.task_id == "test-001"
        assert dequeued.payload["document_id"] == "doc-abc123"

        # After dequeue, status should be PROCESSING
        status = q.get_status("test-001")
        assert status["status"] == TaskStatus.PROCESSING

        print("\n" + "=" * 60)
        print("TASK QUEUE ENQUEUE/DEQUEUE CYCLE:")
        print(f"  Enqueued task_id: {tid}")
        print(f"  Dequeued task_id: {dequeued.task_id}")
        print(f"  Payload match: {dequeued.payload == task.payload}")
        print(f"  Status after dequeue: {status['status']}")
        print(f"STATUS:   PASS")
        print("=" * 60)

    def test_update_status_lifecycle(self):
        """Verify status transitions: PENDING -> PROCESSING -> COMPLETED."""
        q = InMemoryTaskQueue()
        task = TaskPayload(
            task_id="test-002",
            task_type="reindex",
            payload={"case_id": "case-101"}
        )
        q.enqueue(task)

        s1 = q.get_status("test-002")
        assert s1["status"] == TaskStatus.PENDING

        q.update_status("test-002", TaskStatus.PROCESSING)
        s2 = q.get_status("test-002")
        assert s2["status"] == TaskStatus.PROCESSING
        assert "started_at" in s2

        q.update_status("test-002", TaskStatus.COMPLETED)
        s3 = q.get_status("test-002")
        assert s3["status"] == TaskStatus.COMPLETED
        assert "completed_at" in s3

        print("\n" + "=" * 60)
        print("TASK STATUS LIFECYCLE:")
        print(f"  PENDING  -> {s1['status']}")
        print(f"  PROCESSING -> {s2['status']}")
        print(f"  COMPLETED  -> {s3['status']}")
        print(f"STATUS:   PASS")
        print("=" * 60)

    def test_failed_status_with_error(self):
        """Verify FAILED status includes error message."""
        q = InMemoryTaskQueue()
        task = TaskPayload(
            task_id="test-003",
            task_type="analytics",
            payload={"case_id": "case-999"}
        )
        q.enqueue(task)
        q.update_status("test-003", TaskStatus.FAILED, error="Database connection timeout")

        s = q.get_status("test-003")
        assert s["status"] == TaskStatus.FAILED
        assert s["error"] == "Database connection timeout"

        print("\n" + "=" * 60)
        print("TASK FAILURE STATUS:")
        print(f"  Status: {s['status']}")
        print(f"  Error: {s['error']}")
        print(f"STATUS:   PASS")
        print("=" * 60)

    def test_empty_queue_dequeue_returns_none(self):
        """Dequeue from empty queue should return None, not block forever."""
        q = InMemoryTaskQueue()
        result = q.dequeue(timeout=1)
        assert result is None

        print("\n" + "=" * 60)
        print("EMPTY QUEUE DEQUEUE:")
        print(f"  Result: {result}")
        print(f"STATUS:   PASS")
        print("=" * 60)

    def test_get_all_tasks(self):
        """Verify listing all tracked tasks."""
        q = InMemoryTaskQueue()
        for i in range(5):
            q.enqueue(TaskPayload(
                task_id=f"test-list-{i}",
                task_type="document_processing",
                payload={"document_id": f"doc-{i}"}
            ))

        all_tasks = q.get_all_tasks(limit=10)
        assert len(all_tasks) == 5

        print("\n" + "=" * 60)
        print("GET ALL TASKS:")
        print(f"  Task count: {len(all_tasks)}")
        print(f"  IDs: {[t['task_id'] for t in all_tasks]}")
        print(f"STATUS:   PASS")
        print("=" * 60)

    def test_factory_returns_in_memory_without_redis(self):
        """get_task_queue() should fall back to in_memory when Redis is unavailable."""
        import os
        import app.services.ingestion.task_queue as tq_mod
        tq_mod._queue_instance = None
        orig_url = os.environ.get("REDIS_URL")
        os.environ["REDIS_URL"] = "redis://127.0.0.1:19999/0"
        try:
            q = get_task_queue()
            assert q.backend_name == "in_memory"

            print("\n" + "=" * 60)
            print("FACTORY FALLBACK:")
            print(f"  Backend: {q.backend_name}")
            print(f"STATUS:   PASS")
            print("=" * 60)
        finally:
            if orig_url:
                os.environ["REDIS_URL"] = orig_url
            else:
                os.environ.pop("REDIS_URL", None)
            tq_mod._queue_instance = None

    def test_task_payload_serialization(self):
        """TaskPayload round-trips through JSON correctly."""
        task = TaskPayload(
            task_id="test-serial-001",
            task_type="document_processing",
            payload={"document_id": "doc-xyz", "metadata": {"source": "CDR"}}
        )
        json_str = task.to_json()
        restored = TaskPayload.from_json(json_str)

        assert restored.task_id == task.task_id
        assert restored.task_type == task.task_type
        assert restored.payload == task.payload
        assert restored.status == TaskStatus.PENDING

        print("\n" + "=" * 60)
        print("TASK PAYLOAD SERIALIZATION:")
        print(f"  Original ID: {task.task_id}")
        print(f"  Restored ID: {restored.task_id}")
        print(f"  Payload match: {restored.payload == task.payload}")
        print(f"STATUS:   PASS")
        print("=" * 60)
