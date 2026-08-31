"""
NEXUS-CI Task Queue Status API
================================
Endpoints:
  GET  /api/tasks/queue/status    — queue health & active workers
  GET  /api/tasks/queue/health    — alias for status (used by health dashboard)
  GET  /api/tasks/{task_id}       — individual task status
  POST /api/tasks/health-check    — submit a safe health-check job for pipeline verification
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.models.models import User

router = APIRouter(tags=["tasks"])


@router.get("/tasks/queue/status")
def get_queue_status(current_user: User = Depends(get_current_user)):
    """Returns current task queue backend, queue length, active workers, and recent tasks."""
    from app.services.ingestion.task_queue import get_task_queue, get_queue_health
    health = get_queue_health()
    queue = get_task_queue()
    return {
        **health,
        "recentTasks": queue.get_all_tasks(limit=20),
    }


@router.get("/tasks/queue/health")
def get_queue_health_endpoint(current_user: User = Depends(get_current_user)):
    """Safe queue infrastructure health check."""
    from app.services.ingestion.task_queue import get_queue_health
    return get_queue_health()


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """Returns status of a specific task by task_id."""
    from app.services.ingestion.task_queue import get_task_queue
    queue = get_task_queue()
    status = queue.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return status


@router.post("/tasks/health-check")
def submit_health_check_job(current_user: User = Depends(get_current_user)):
    """
    Submit a safe health-check job to verify the end-to-end queue pipeline.
    Returns the task_id for status polling.
    """
    from app.services.ingestion.task_queue import create_task
    task_id = create_task(
        task_type="health_check",
        payload={"submitted_by": current_user.id, "note": "pipeline_verification"},
        max_retries=1,
    )
    return {
        "task_id":   task_id,
        "task_type": "health_check",
        "status":    "queued",
        "message":   "Health-check job submitted. Poll GET /api/tasks/{task_id} for status.",
    }

