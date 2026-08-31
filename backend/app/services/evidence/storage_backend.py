"""
NEXUS-CI Object Storage Abstraction — Production
=================================================
Backends:
  - LocalStorageBackend: File system storage under UPLOAD_DIR with path-traversal protection.
  - S3StorageBackend   : S3-compatible object storage via boto3 with pre-signed URL generation.

Deterministic Key Convention:
  cases/{case_id}/documents/{document_id}/v{version}/{filename}
"""
import os
import re
import hashlib
import threading
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


def calculate_sha256(data: bytes) -> str:
    """Returns hexadecimal SHA-256 hash of binary data."""
    return hashlib.sha256(data).hexdigest()


def make_storage_key(case_id: str, document_id: str, filename: str, version: int = 1) -> str:
    """
    Constructs a deterministic, safe storage key.
    Enforces pattern: cases/{case_id}/documents/{document_id}/v{version}/{sanitized_filename}
    """
    safe_case = re.sub(r"[^a-zA-Z0-9_-]", "_", str(case_id or "global"))
    safe_doc = re.sub(r"[^a-zA-Z0-9_-]", "_", str(document_id or "doc"))
    safe_filename = os.path.basename(filename or "file.bin")
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_filename)
    return f"cases/{safe_case}/documents/{safe_doc}/v{version}/{safe_filename}"


class BaseStorageBackend(ABC):
    """Abstract base for object storage backends."""
    backend_name: str = "base"

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Save bytes to storage. Returns storage location string."""
        ...

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Alias for save()."""
        return self.save(key, data, content_type)

    @abstractmethod
    def load(self, key: str) -> Optional[bytes]:
        """Load bytes from storage. Returns None if key not found."""
        ...

    def download(self, key: str) -> Optional[bytes]:
        """Alias for load()."""
        return self.load(key)

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in storage."""
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from storage. Returns True if deleted."""
        ...

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get canonical URL or path for stored object."""
        ...

    @abstractmethod
    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a short-lived URL for downloading the object."""
        ...


class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.
    Enforces strict path-traversal prevention: resolved absolute paths MUST remain
    inside base_dir.
    """
    backend_name = "local"

    def __init__(self, base_dir: str = "./uploads"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, key: str) -> str:
        """
        Resolves absolute file path and verifies it does not escape base_dir.
        Strips path traversal elements (..) and ensures target path remains inside base_dir.
        """
        clean_key = key.replace("\\", "/").lstrip("/")
        # Filter out empty parts, '.', and '..'
        parts = [p for p in clean_key.split("/") if p not in ("", ".", "..")]
        safe_relative = os.path.join(*parts) if parts else "unnamed.bin"
        target_path = os.path.abspath(os.path.join(self.base_dir, safe_relative))

        if not target_path.startswith(self.base_dir):
            raise ValueError(f"Path traversal detected: '{key}' resolves outside base directory")
        return target_path

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._resolve_safe_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load(self, key: str) -> Optional[bytes]:
        path = self._resolve_safe_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        try:
            path = self._resolve_safe_path(key)
            return os.path.exists(path)
        except ValueError:
            return False

    def delete(self, key: str) -> bool:
        try:
            path = self._resolve_safe_path(key)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except ValueError:
            return False

    def get_url(self, key: str) -> str:
        return self._resolve_safe_path(key)

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        # Local backend returns API download route with key reference
        clean_key = key.replace("\\", "/").lstrip("/")
        return f"/api/evidence/download-local?key={clean_key}&expires={expires_in}"


class S3StorageBackend(BaseStorageBackend):
    """
    S3-compatible object storage backend (AWS S3, MinIO, Ceph, Wasabi).
    Uses boto3 for all S3 interactions and pre-signed URL generation.
    """
    backend_name = "s3"

    def __init__(
        self,
        bucket: str,
        endpoint_url: str = "",
        access_key: str = "",
        secret_key: str = "",
        region: str = "ap-south-1"
    ):
        import boto3
        from botocore.config import Config

        self.bucket = bucket.strip()
        if not self.bucket:
            raise ValueError("S3_BUCKET is required for S3StorageBackend")

        client_kwargs: Dict[str, Any] = {
            "region_name": region or "ap-south-1",
            "config": Config(signature_version="s3v4"),
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key

        self._client = boto3.client("s3", **client_kwargs)

        # Probe bucket accessibility
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception as exc:
            # Attempt bucket creation if head fails
            try:
                if region and region != "us-east-1":
                    self._client.create_bucket(
                        Bucket=self.bucket,
                        CreateBucketConfiguration={"LocationConstraint": region}
                    )
                else:
                    self._client.create_bucket(Bucket=self.bucket)
            except Exception as create_exc:
                # If creation also fails, propagate error for strict mode
                raise RuntimeError(
                    f"S3 bucket '{self.bucket}' inaccessible and creation failed: {exc} | {create_exc}"
                ) from exc

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        clean_key = key.replace("\\", "/").lstrip("/")
        self._client.put_object(
            Bucket=self.bucket,
            Key=clean_key,
            Body=data,
            ContentType=content_type
        )
        return f"s3://{self.bucket}/{clean_key}"

    def load(self, key: str) -> Optional[bytes]:
        clean_key = key.replace("\\", "/").lstrip("/")
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=clean_key)
            return resp["Body"].read()
        except Exception:
            return None

    def exists(self, key: str) -> bool:
        clean_key = key.replace("\\", "/").lstrip("/")
        try:
            self._client.head_object(Bucket=self.bucket, Key=clean_key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        clean_key = key.replace("\\", "/").lstrip("/")
        try:
            self._client.delete_object(Bucket=self.bucket, Key=clean_key)
            return True
        except Exception:
            return False

    def get_url(self, key: str) -> str:
        clean_key = key.replace("\\", "/").lstrip("/")
        return f"s3://{self.bucket}/{clean_key}"

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        clean_key = key.replace("\\", "/").lstrip("/")
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": clean_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as exc:
            raise RuntimeError(f"Failed to generate presigned S3 URL for '{clean_key}': {exc}") from exc


# ── Singleton & Factory ────────────────────────────────────────────────────────

_storage_instance: Optional[BaseStorageBackend] = None
_storage_lock = threading.Lock()


def reset_storage_instance() -> None:
    """Force reset singleton instance (used by unit tests)."""
    global _storage_instance
    with _storage_lock:
        _storage_instance = None


def get_storage_backend() -> BaseStorageBackend:
    """
    Factory returning configured storage backend instance.

    Policy:
      1. STORAGE_BACKEND="local" → LocalStorageBackend
      2. STORAGE_BACKEND="s3"    → S3StorageBackend (raises if boto3/bucket error)
      3. STORAGE_BACKEND empty   → Auto-detect: try S3 if S3_BUCKET set, else local
    """
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    with _storage_lock:
        if _storage_instance is not None:
            return _storage_instance

        backend_mode = os.getenv("STORAGE_BACKEND", "").strip().lower()
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")

        if backend_mode == "local":
            _storage_instance = LocalStorageBackend(upload_dir)
            print(f"[STORAGE] Backend: LOCAL ({_storage_instance.base_dir})")
        elif backend_mode == "s3":
            # Explicit S3 mode — raise if credentials/bucket fail (strict mode)
            _storage_instance = S3StorageBackend(
                bucket=os.getenv("S3_BUCKET", "nexus-ci-evidence"),
                endpoint_url=os.getenv("S3_ENDPOINT", ""),
                access_key=os.getenv("S3_ACCESS_KEY", ""),
                secret_key=os.getenv("S3_SECRET_KEY", ""),
                region=os.getenv("S3_REGION", "ap-south-1"),
            )
            print(f"[STORAGE] Backend: S3 (bucket={_storage_instance.bucket})")
        else:
            # Auto-detect
            bucket = os.getenv("S3_BUCKET", "").strip()
            access_key = os.getenv("S3_ACCESS_KEY", "").strip()
            if bucket and access_key:
                try:
                    _storage_instance = S3StorageBackend(
                        bucket=bucket,
                        endpoint_url=os.getenv("S3_ENDPOINT", ""),
                        access_key=access_key,
                        secret_key=os.getenv("S3_SECRET_KEY", ""),
                        region=os.getenv("S3_REGION", "ap-south-1"),
                    )
                    print(f"[STORAGE] Backend: S3 (auto-detected, bucket={_storage_instance.bucket})")
                except Exception as exc:
                    _storage_instance = LocalStorageBackend(upload_dir)
                    print(f"[STORAGE] S3 init failed ({exc}); Backend: LOCAL (fallback)")
            else:
                _storage_instance = LocalStorageBackend(upload_dir)
                print(f"[STORAGE] Backend: LOCAL ({_storage_instance.base_dir})")

        return _storage_instance


def get_storage_status() -> Dict[str, Any]:
    """Safe diagnostic endpoint payload."""
    try:
        backend = get_storage_backend()
        is_s3 = backend.backend_name == "s3"
        return {
            "backend":          backend.backend_name.upper(),
            "is_s3":            is_s3,
            "base_dir":         getattr(backend, "base_dir", None),
            "s3_bucket":        getattr(backend, "bucket", None),
            "signed_url_supported": True,
            "configured":       True,
            "status":           "ready",
        }
    except Exception as exc:
        return {
            "backend":          "UNCONFIGURED",
            "is_s3":            False,
            "signed_url_supported": False,
            "configured":       False,
            "status":           f"Error: {exc}",
        }
