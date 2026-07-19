import os
import sys
import json
import select
import subprocess
import time
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Zepto PRDE Backend API",
    description="FastAPI backend for Zepto AI-Powered Cross-Category Review Discovery Engine",
    version="1.0.0"
)

# Enable CORS for Next.js frontend communication (usually localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Zepto AI-Powered Cross-Category Review Discovery Engine (PRDE) Backend API",
        "version": "1.0.0"
    }

@app.get("/api/dashboard")
def get_dashboard():
    """Reads the generated dashboard JSON data and serves it."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_path = os.path.join(project_root, "data", "dashboard_data.json")

    if not os.path.exists(data_path):
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard data file not found at: {data_path}. Please run the pipeline first."
        )

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading dashboard data: {str(e)}"
        )


# Interval (seconds) between SSE heartbeat pings when no pipeline output arrives.
# Must be well under Render's idle-connection timeout (~30 s) to prevent the proxy
# from closing a silent SSE stream during Groq rate-limit sleeps.
_SSE_HEARTBEAT_INTERVAL = 15


@app.post("/api/run-pipeline")
def run_pipeline():
    """Spawns the python E2E orchestrator pipeline and streams stdout/stderr logs."""

    def log_generator():
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script_path = os.path.join(project_root, "src", "main.py")

        # Determine python execution path (using venv if available)
        python_exec = sys.executable or "python"
        win_venv_python = os.path.join(project_root, "venv", "Scripts", "python.exe")
        unix_venv_python = os.path.join(project_root, "venv", "bin", "python")
        unix_dot_venv_python = os.path.join(project_root, ".venv", "bin", "python")

        if os.path.exists(win_venv_python):
            python_exec = win_venv_python
        elif os.path.exists(unix_venv_python):
            python_exec = unix_venv_python
        elif os.path.exists(unix_dot_venv_python):
            python_exec = unix_dot_venv_python

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Disable Python print buffering so logs stream instantly

        yield json.dumps({"type": "system", "text": "Initializing pipeline process..."}) + "\n"
        yield json.dumps({"type": "system", "text": f"Invoking script: {python_exec} src/main.py --phase all"}) + "\n"

        proc = None
        try:
            # Merge stderr into stdout so they stream in chronological order
            proc = subprocess.Popen(
                [python_exec, script_path, "--phase", "all"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )

            # ── Non-blocking read loop with SSE heartbeat ────────────────────
            #
            # Problem: proc.stdout.readline() blocks until a line arrives.
            # When the pipeline sleeps (e.g. Groq rate-limit backoffs of 5-30 s),
            # no output is produced and the SSE stream goes silent.  Render's
            # proxy/load-balancer closes idle connections after ~30 s, which
            # makes the UI appear "stuck" even though the process is still running.
            #
            # Fix: use select() to poll stdout with a short timeout.  If nothing
            # arrives within _SSE_HEARTBEAT_INTERVAL seconds, emit an SSE comment
            # (": ping") to keep the TCP connection alive without adding noise to
            # the UI log.
            #
            # select() is unavailable on Windows, so we fall back to the original
            # blocking readline() on that platform (no proxy timeout issue locally).
            # ────────────────────────────────────────────────────────────────────
            use_select = hasattr(select, "select") and sys.platform != "win32"

            while True:
                if use_select:
                    ready, _, _ = select.select(
                        [proc.stdout], [], [], _SSE_HEARTBEAT_INTERVAL
                    )
                    if ready:
                        line = proc.stdout.readline()
                    else:
                        # Timeout — no output yet
                        if proc.poll() is not None:
                            break
                        # Emit SSE heartbeat comment to prevent proxy timeout.
                        # SSE comment lines start with ":" and are ignored by
                        # EventSource clients but keep the TCP connection alive.
                        yield ": ping\n\n"
                        continue
                else:
                    # Windows fallback: blocking read
                    line = proc.stdout.readline()

                if not line and proc.poll() is not None:
                    break
                if line:
                    yield json.dumps({"type": "stdout", "text": line.rstrip("\n")}) + "\n"

            exit_code = proc.wait()
            yield json.dumps({"type": "close", "code": exit_code}) + "\n"

        except Exception as e:
            yield json.dumps({"type": "error", "text": f"Backend Server error spawning process: {str(e)}"}) + "\n"
            yield json.dumps({"type": "close", "code": -1}) + "\n"
        finally:
            if proc is not None and proc.poll() is None:
                logger.info("Client disconnected or generator closed. Terminating pipeline subprocess...")
                try:
                    proc.terminate()
                    for _ in range(50):
                        if proc.poll() is not None:
                            break
                        time.sleep(0.1)
                    if proc.poll() is None:
                        proc.kill()
                except Exception as cleanup_err:
                    logger.error(f"Error terminating subprocess: {cleanup_err}")

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(log_generator(), media_type="text/event-stream", headers=headers)
