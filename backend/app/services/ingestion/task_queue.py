"""
NEXUS-CI Task Queue Abstraction — Production
============================================
Backends:
  - RedisTaskQueue   : Real Redis LIST + HASH backed queue.
  - InMemoryTaskQueue: Thread-safe in-process queue for unit-tests/offline dev.

Key design decisions:
  - Backend selected EXPLICITLY via QUEUE_BACKEND env var ("redis" or "in_memory").
  - Idempotency: jobs with the same idempotency_key are deduplicated.
  - Retry: bounded retry count per job.
  - Heartbeat: workers publish a timestamp; health API reads it.
  - Payloads in Redis contain only references (document_id, case_id), not file contents.
"""
import json
import uuid
import datetime
import threading
from enum import Enum
from queue import Queue, Empty
from typing import Dict, Any, Optional, List


class TaskStatus(str, Enum):
    PENDING    = "pending"
    QUEUED     = "queued"
    PROCESSING = "processing"
    RETRYING   = "retrying"
    COMPLETED  = "completed"
    FAILED     = "failed"


class TaskPayload:
    """
    Durable task descriptor.
    Only lightweight references go into Redis; large binary data lives in storage.
    """
    FIELDS = (
        "task_id", "task_type", "payload", "status",
        "created_at", "started_at", "completed_at",
        "retry_count", "max_retries", "error",
        "idempotency_key", "worker_id", "case_id", "document_id",
    )

    def __init__(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        status: str = TaskStatus.PENDING,
        created_at: str = "",
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        error: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        worker_id: Optional[str] = None,
        case_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ):
        self.task_id         = task_id
        self.task_type       = task_type
        self.payload         = payload
        self.status          = status
        self.created_at      = created_at or datetime.datetime.now(datetime.UTC).isoformat()
        self.started_at      = started_at
        self.completed_at    = completed_at
        self.retry_count     = retry_count
        self.max_retries     = max_retries
        self.error           = error
        self.idempotency_key = idempotency_key
        self.worker_id       = worker_id
        self.case_id         = case_id or payload.get("case_id")
        self.document_id     = document_id or payload.get("document_id")

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.FIELDS}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TaskPayload":
        valid = {k: v for k, v in d.items() if k in cls.FIELDS}
        return cls(**valid)

    @classmethod
    def from_json(cls, data: str) -> "TaskPayload":
        return cls.from_dict(json.loads(data))


class BaseTaskQueue:
    """Abstract base for task queue backends."""
    backend_name: str = "base"

    def enqueue(self, task: TaskPayload) -> str:
        raise NotImplementedError

    def dequeue(self, timeout: int = 1) -> Optional[TaskPayload]:
        raise NotImplementedError

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def update_status(
        self, task_id: str, status: "TaskStatus",
        error: Optional[str] = None, worker_id: Optional[str] = None,
    ) -> None:
        raise NotImplementedError

    def get_queue_length(self) -> int:
        raise NotImplementedError

    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def ping(self) -> bool:
        return True

    def publish_heartbeat(self, worker_id: str) -> None:
        pass

    def get_worker_heartbeat(self, worker_id: str) -> Optional[str]:
        return None

    def list_active_workers(self, ttl_seconds: int = 30) -> List[str]:
        return []


class RedisTaskQueue(BaseTaskQueue):
    """
    Redis-backed task queue.

    Data structures:
      nexus:queue               LIST   – FIFO via LPUSH / BRPOP
      nexus:task:{id}           HASH   – durable task status (24h TTL)
      nexus:idem:{key}          STRING – idempotency lock (24h TTL)
      nexus:task_index          SET    – all task IDs for listing
      nexus:heartbeat:{wid}     STRING – worker last-seen timestamp
      nexus:workers             SET    – active worker IDs
    """
    backend_name = "redis"

    QUEUE_KEY     = "nexus:queue"
    TASK_PREFIX   = "nexus:task:"
    IDEM_PREFIX   = "nexus:idem:"
    INDEX_KEY     = "nexus:task_index"
    HB_PREFIX     = "nexus:heartbeat:"
    WORKERS_KEY   = "nexus:workers"
    TASK_TTL      = 86400
    IDEM_TTL      = 86400
    HEARTBEAT_TTL = 60

    def __init__(self, redis_url: str):
        import redis as redis_lib
        self._redis = redis_lib.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self._redis.ping()   # Raises ConnectionError on failure — caller handles it

    def ping(self) -> bool:
        try:
            return bool(self._redis.ping())
        except Exception:
            return False

    def _is_duplicate(self, idempotency_key: Optional[str]) -> bool:
        if not idempotency_key:
            return False
        set_result = self._redis.set(
            f"{self.IDEM_PREFIX}{idempotency_key}", "1",
            nx=True, ex=self.IDEM_TTL,
        )
        return set_result is None   # None = already existed = duplicate

    def enqueue(self, task: TaskPayload) -> str:
        if self._is_duplicate(task.idempotency_key):
            return task.task_id   # Deduplicated — no re-queue

        task.status = TaskStatus.PENDING
        status_str = task.status.value if hasattr(task.status, "value") else str(task.status)
        task_key = f"{self.TASK_PREFIX}{task.task_id}"
        self._redis.hset(task_key, mapping={
            "task_id":         task.task_id,
            "task_type":       task.task_type,
            "status":          status_str,
            "created_at":      task.created_at,
            "retry_count":     str(task.retry_count),
            "max_retries":     str(task.max_retries),
            "payload":         json.dumps(task.payload),
            "idempotency_key": task.idempotency_key or "",
            "worker_id":       task.worker_id or "",
            "case_id":         task.case_id or "",
            "document_id":     task.document_id or "",
        })
        self._redis.expire(task_key, self.TASK_TTL)
        self._redis.sadd(self.INDEX_KEY, task.task_id)
        self._redis.lpush(self.QUEUE_KEY, task.to_json())
        return task.task_id

    def dequeue(self, timeout: int = 1) -> Optional[TaskPayload]:
        result = self._redis.brpop(self.QUEUE_KEY, timeout=timeout)
        if result:
            _, data = result
            task = TaskPayload.from_json(data)
            self.update_status(task.task_id, TaskStatus.PROCESSING)
            return task
        return None

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        data = self._redis.hgetall(f"{self.TASK_PREFIX}{task_id}")
        if data:
            return {
                "task_id":      data.get("task_id"),
                "task_type":    data.get("task_type"),
                "status":       data.get("status"),
                "created_at":   data.get("created_at"),
                "started_at":   data.get("started_at"),
                "completed_at": data.get("completed_at"),
                "retry_count":  int(data.get("retry_count", 0)),
                "max_retries":  int(data.get("max_retries", 3)),
                "error":        data.get("error"),
                "worker_id":    data.get("worker_id"),
                "case_id":      data.get("case_id"),
                "document_id":  data.get("document_id"),
            }
        return None

    def update_status(
        self, task_id: str, status: "TaskStatus",
        error: Optional[str] = None, worker_id: Optional[str] = None,
    ) -> None:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        task_key = f"{self.TASK_PREFIX}{task_id}"
        status_str = status.value if hasattr(status, "value") else str(status)
        updates: Dict[str, str] = {"status": status_str}
        if status == TaskStatus.PROCESSING:
            updates["started_at"] = now
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            updates["completed_at"] = now
        if status == TaskStatus.RETRYING:
            self._redis.hincrby(task_key, "retry_count", 1)
        if error is not None:
            updates["error"] = str(error)[:500]
        if worker_id:
            updates["worker_id"] = worker_id
        self._redis.hset(task_key, mapping=updates)

    def get_queue_length(self) -> int:
        return self._redis.llen(self.QUEUE_KEY)

    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        task_ids = list(self._redis.smembers(self.INDEX_KEY))[:limit]
        results = [s for tid in task_ids if (s := self.get_status(tid))]
        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

    # ── Heartbeat ─────────────────────────────────────────────────────
    def publish_heartbeat(self, worker_id: str) -> None:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        self._redis.set(f"{self.HB_PREFIX}{worker_id}", now, ex=self.HEARTBEAT_TTL)
        self._redis.sadd(self.WORKERS_KEY, worker_id)

    def get_worker_heartbeat(self, worker_id: str) -> Optional[str]:
        return self._redis.get(f"{self.HB_PREFIX}{worker_id}")

    def list_active_workers(self, ttl_seconds: int = 30) -> List[str]:
        worker_ids = self._redis.smembers(self.WORKERS_KEY)
        cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=ttl_seconds)
        active = []
        for wid in worker_ids:
            ts_str = self._redis.get(f"{self.HB_PREFIX}{wid}")
            if ts_str:
                try:
                    if datetime.datetime.fromisoformat(ts_str) >= cutoff:
                        active.append(wid)
                except ValueError:
                    pass
        return active


class InMemoryTaskQueue(BaseTaskQueue):
    """
    Thread-safe in-memory task queue.
    FOR UNIT-TESTS AND OFFLINE DEVELOPMENT ONLY.
    Will never be labelled "redis" in status responses.
    """
    backend_name = "in_memory"

    def __init__(self):
        self._queue: Queue = Queue()
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._idem_keys: set = set()
        self._lock = threading.Lock()

    def ping(self) -> bool:
        return True

    def enqueue(self, task: TaskPayload) -> str:
        if task.idempotency_key:
            with self._lock:
                if task.idempotency_key in self._idem_keys:
                    return task.task_id
                self._idem_keys.add(task.idempotency_key)

        task.status = TaskStatus.PENDING
        status_str = task.status.value if hasattr(task.status, "value") else str(task.status)
        with self._lock:
            self._statuses[task.task_id] = {
                "task_id":      task.task_id,
                "task_type":    task.task_type,
                "status":       status_str,
                "created_at":   task.created_at,
                "started_at":   None,
                "completed_at": None,
                "retry_count":  task.retry_count,
                "max_retries":  task.max_retries,
                "error":        task.error,
                "worker_id":    task.worker_id,
                "case_id":      task.case_id,
                "document_id":  task.document_id,
                "payload":      task.payload,
            }
        self._queue.put(task)
        return task.task_id

    def dequeue(self, timeout: int = 1) -> Optional[TaskPayload]:
        try:
            task = self._queue.get(timeout=timeout)
            self.update_status(task.task_id, TaskStatus.PROCESSING)
            return task
        except Empty:
            return None

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._statuses[task_id]) if task_id in self._statuses else None

    def update_status(
        self, task_id: str, status: "TaskStatus",
        error: Optional[str] = None, worker_id: Optional[str] = None,
    ) -> None:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        status_str = status.value if hasattr(status, "value") else str(status)
        with self._lock:
            if task_id not in self._statuses:
                return
            self._statuses[task_id]["status"] = status_str
            if status == TaskStatus.PROCESSING:
                self._statuses[task_id]["started_at"] = now
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._statuses[task_id]["completed_at"] = now
            if status == TaskStatus.RETRYING:
                self._statuses[task_id]["retry_count"] = \
                    self._statuses[task_id].get("retry_count", 0) + 1
            if error is not None:
                self._statuses[task_id]["error"] = str(error)
            if worker_id:
                self._statuses[task_id]["worker_id"] = worker_id

    def get_queue_length(self) -> int:
        return self._queue.qsize()

    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            items = sorted(
                self._statuses.values(),
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )
            return [dict(x) for x in items[:limit]]


# ── Singleton factory ──────────────────────────────────────────────────────────

_queue_instance: Optional[BaseTaskQueue] = None
_queue_lock = threading.Lock()


def reset_queue_instance() -> None:
    """Force re-initialization — used by tests only."""
    global _queue_instance
    with _queue_lock:
        _queue_instance = None


def get_task_queue() -> BaseTaskQueue:
    """
    Factory returning the configured task queue backend.

    Selection (in priority order):
      1. QUEUE_BACKEND="in_memory"  → always use InMemoryTaskQueue
      2. QUEUE_BACKEND="redis"      → Redis required; raise if unavailable
      3. QUEUE_BACKEND not set      → try Redis; warn and fall back to in_memory
    """
    global _queue_instance
    if _queue_instance is not None:
        return _queue_instance

    with _queue_lock:
        if _queue_instance is not None:
            return _queue_instance

        import os
        explicit_backend = os.getenv("QUEUE_BACKEND", "").strip().lower()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        if explicit_backend == "in_memory":
            _queue_instance = InMemoryTaskQueue()
            print("[TASK QUEUE] Backend: IN_MEMORY (explicitly configured)")
        elif explicit_backend == "redis":
            # Explicit Redis — do NOT silently fall back
            _queue_instance = RedisTaskQueue(redis_url)
            print(f"[TASK QUEUE] Backend: REDIS ({redis_url})")
        else:
            # Auto-detect
            try:
                _queue_instance = RedisTaskQueue(redis_url)
                print(f"[TASK QUEUE] Backend: REDIS (auto-detected, {redis_url})")
            except Exception as exc:
                _queue_instance = InMemoryTaskQueue()
                print(f"[TASK QUEUE] Redis unavailable ({exc}); Backend: IN_MEMORY (fallback)")

        return _queue_instance


def create_task(
    task_type: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    max_retries: int = 3,
) -> str:
    """Convenience helper: create and enqueue a task, returning its ID."""
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    task = TaskPayload(
        task_id=task_id,
        task_type=task_type,
        payload=payload,
        idempotency_key=idempotency_key,
        max_retries=max_retries,
    )
    get_task_queue().enqueue(task)
    return task_id


def get_queue_health() -> Dict[str, Any]:
    """Returns safe health payload without exposing secrets."""
    import os
    try:
        queue = get_task_queue()
        is_redis = queue.backend_name == "redis"
        active_workers = queue.list_active_workers(ttl_seconds=30)
        return {
            "backend":        queue.backend_name.upper(),
            "is_real_redis":  is_redis,
            "redis_ping":     queue.ping() if is_redis else None,
            "queue_length":   queue.get_queue_length(),
            "active_workers": active_workers,
            "worker_status":  "ONLINE" if active_workers else "OFFLINE",
            "queue_status":   "READY" if queue.ping() else "DEGRADED",
            "redis_url_set":  bool(os.getenv("REDIS_URL")),
        }
    except Exception as exc:
        return {
            "backend":        "UNKNOWN",
            "is_real_redis":  False,
            "redis_ping":     False,
            "queue_length":   -1,
            "active_workers": [],
            "worker_status":  "OFFLINE",
        }
