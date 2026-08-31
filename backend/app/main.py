from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.db.postgres import init_db
from app.api import (
    auth, cases, evidence, entities, graph, findings, timeline,
    paths, resolution, copilot, audit, historical, analytics, rag, ai, sync, reports, websocket, workspace, tasks
)

# Initialize database tables and non-destructive schema migrations
init_db()

app = FastAPI(
    title="NEXUS-CI API",
    description="Evidence-Centric AI Criminal Intelligence Platform Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon, allow all. In production restrict to NextJS host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting + security headers middleware
from app.core.security_middleware import RateLimitMiddleware
import os
_rpm = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
app.add_middleware(RateLimitMiddleware, requests_per_minute=_rpm)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(entities.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")
app.include_router(paths.router, prefix="/api")
app.include_router(resolution.router, prefix="/api")
app.include_router(copilot.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(historical.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(workspace.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(websocket.router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "NEXUS-CI Core Backend"}

@app.get("/api/health/deep")
def deep_health_check():
    """Comprehensive subsystem health check for monitoring dashboards."""
    from app.core.observability import check_health_deep
    return check_health_deep()


# Global exception interceptor to satisfy Rule 40: "Error Handling"
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc)
    print(f"Server Error occurred: {error_msg}")
    
    # Check if this looks like a pipeline/parser fail
    if "parser" in error_msg.lower() or "csv" in error_msg.lower() or "pdf" in error_msg.lower():
        user_message = f"Analysis failed during processing: {error_msg}. The original evidence remains safely stored."
    else:
        user_message = "An analytical pipeline exception was encountered on the server. The data integrity remains secure."
        
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": user_message}
    )
