"""In-memory job store for the blog pipeline.

Thread-safe dict-based store with create/get/update/delete/list/cancel methods.
"""
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class _JobStore:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, job_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        with self._lock:
            jid = job_id or str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            job = {
                "job_id": jid,
                "status": JobStatus.PENDING.value,
                "created_at": now,
                "updated_at": now,
                "result": None,
                "error": None,
                "progress": None,
            }
            job.update(kwargs)
            # Ensure status is stored as string
            if isinstance(job.get("status"), JobStatus):
                job["status"] = job["status"].value
            # Ensure service_type is stored as string
            st = job.get("service_type")
            if st and hasattr(st, "value"):
                job["service_type"] = st.value
            self._jobs[jid] = job
            return job

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for k, v in kwargs.items():
                if isinstance(v, JobStatus):
                    v = v.value
                if hasattr(v, "value") and k == "service_type":
                    v = v.value
                job[k] = v
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            return job

    def delete(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def list_all(self, service_type=None, status=None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        # Filter
        if service_type is not None:
            st_val = service_type.value if hasattr(service_type, "value") else service_type
            jobs = [j for j in jobs if j.get("service_type") == st_val]
        if status is not None:
            st_val = status.value if hasattr(status, "value") else status
            jobs = [j for j in jobs if j.get("status") == st_val]
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return jobs[:limit]

    def cancel(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job["status"] = JobStatus.CANCELLED.value
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            return job


job_store = _JobStore()
