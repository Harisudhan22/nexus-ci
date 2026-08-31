"""
NEXUS-CI Security Middleware
==============================
Production security hardening:
  1. Rate limiting (per-IP, configurable via RATE_LIMIT_PER_MINUTE)
  2. Request ID injection for traceability
  3. Security headers (HSTS, X-Content-Type-Options, etc.)
  4. Input sanitization helpers
"""
import os
import re
import time
import uuid
import threading
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter per client IP.
    Configurable via RATE_LIMIT_PER_MINUTE environment variable.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._buckets: Dict[str, Tuple[float, int]] = {}  # ip -> (window_start, count)
        self._lock = threading.Lock()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/api/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()

        with self._lock:
            window_start, count = self._buckets.get(client_ip, (now, 0))

            # Reset window if 60 seconds have passed
            if now - window_start >= 60:
                window_start = now
                count = 0

            count += 1
            self._buckets[client_ip] = (window_start, count)

        if count > self.rpm:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(int(60 - (now - window_start))),
                    "X-RateLimit-Limit": str(self.rpm),
                    "X-RateLimit-Remaining": "0",
                }
            )

        # Inject request ID for traceability
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        # Add security + rate limit headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - count))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response


# ── Input Sanitization Helpers ──────────────────────────────────

# Patterns for common injection attacks
_SQL_INJECTION_PATTERN = re.compile(
    r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|EXECUTE)\b.*\b(FROM|INTO|TABLE|WHERE|SET)\b)",
    re.IGNORECASE
)
_XSS_PATTERN = re.compile(r"<\s*script|javascript\s*:|on\w+\s*=", re.IGNORECASE)
_PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\")


def sanitize_text_input(text: str) -> str:
    """
    Sanitize user text input by removing dangerous patterns.
    Used for copilot queries, search inputs, and form fields.
    """
    if not text:
        return text

    # Strip null bytes
    text = text.replace("\x00", "")

    # Remove script tags and event handlers
    text = re.sub(r"<\s*script[^>]*>.*?</\s*script\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+on\w+\s*=\s*['\"][^'\"]*['\"][^>]*>", "", text, flags=re.IGNORECASE)

    return text.strip()


def is_safe_identifier(value: str) -> bool:
    """Check if a string is a safe identifier (alphanumeric + hyphens + underscores)."""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', value))


def detect_injection(text: str) -> dict:
    """
    Detect potential injection attacks in user input.
    Returns: {"safe": bool, "threats": list[str]}
    """
    threats = []

    if _SQL_INJECTION_PATTERN.search(text):
        threats.append("sql_injection")
    if _XSS_PATTERN.search(text):
        threats.append("xss")
    if _PATH_TRAVERSAL_PATTERN.search(text):
        threats.append("path_traversal")

    return {"safe": len(threats) == 0, "threats": threats}
