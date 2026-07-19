"""
Integration test for Phase 6: Frontend + Backend API validation.
Starts the Next.js dev server, waits for it to be ready,
then tests all routes and the API endpoint.
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
BASE_URL = "http://localhost:3000"
SERVER_STARTUP_TIMEOUT = 60   # seconds to wait for server to be ready
SERVER_POLL_INTERVAL = 2      # seconds between readiness polls

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def status(msg):
    print(msg, flush=True)

def ok(msg):
    print(f"  [OK] {msg}", flush=True)

def fail(msg):
    print(f"  [FAIL] {msg}", flush=True)

def section(title):
    print(f"\n{'─' * 60}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'─' * 60}", flush=True)

def http_get(path, timeout=35):
    """Returns (status_code, body_str) or raises."""
    url = BASE_URL + path
    req = urllib.request.Request(url, headers={"User-Agent": "PRDE-IntegrationTest/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8")

def wait_for_server(timeout=SERVER_STARTUP_TIMEOUT):
    """Poll /api/dashboard until it responds or times out."""
    status(f"\n[...] Waiting up to {timeout}s for Next.js server to be ready at {BASE_URL} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            code, _ = http_get("/api/dashboard", timeout=3)
            if code == 200:
                ok(f"Server is ready (HTTP {code})")
                return True
        except Exception:
            pass
        time.sleep(SERVER_POLL_INTERVAL)
    return False

# ─────────────────────────────────────────────────────────────
# Individual test cases
# ─────────────────────────────────────────────────────────────

def test_api_dashboard():
    section("Test 1 — GET /api/dashboard")
    code, body = http_get("/api/dashboard")
    assert code == 200, f"Expected HTTP 200, got {code}"
    ok(f"HTTP status: {code}")

    data = json.loads(body)

    # Top-level keys
    required_top = {"week_ending", "pulse_note_text", "metrics", "total_reviews_analyzed", "product_discovery_relevant_reviews", "sentiment_distribution"}
    missing_top = required_top - set(data.keys())
    assert not missing_top, f"Missing top-level keys: {missing_top}"
    ok(f"Top-level keys present: {sorted(required_top)}")

    # Metrics keys (Zepto Q-Commerce)
    required_metrics = {
        "repeat_purchase_drivers", "exploration_barriers", "discovery_methods",
        "habit_drivers", "information_needs", "top_frustrations", 
        "underserved_segments", "unmet_needs", "opportunities"
    }
    missing_metrics = required_metrics - set(data["metrics"].keys())
    assert not missing_metrics, f"Missing metrics keys: {missing_metrics}"
    ok(f"All 9 metrics keys present")

    # week_ending format
    we = data["week_ending"]
    assert len(we) == 10 and we[4] == "-" and we[7] == "-", f"Unexpected week_ending format: {we}"
    ok(f"week_ending format valid: {we}")

    # pulse_note_text is non-empty
    assert len(data["pulse_note_text"]) > 50, "pulse_note_text is too short or empty"
    ok(f"pulse_note_text length: {len(data['pulse_note_text'])} chars")
    return True

def test_dashboard_page():
    section("Test 2 — GET /dashboard (HTML page)")
    code, body = http_get("/dashboard")
    assert code == 200, f"Expected HTTP 200, got {code}"
    ok(f"HTTP status: {code}")
    assert "<html" in body.lower(), "Response does not look like HTML"
    ok("Response contains HTML markup")
    return True

def test_pulse_note_page():
    section("Test 3 — GET /pulse-note (HTML page)")
    code, body = http_get("/pulse-note")
    assert code == 200, f"Expected HTTP 200, got {code}"
    ok(f"HTTP status: {code}")
    assert "<html" in body.lower(), "Response does not look like HTML"
    ok("Response contains HTML markup")
    return True

def test_opportunities_page():
    section("Test 4 — GET /opportunities (HTML page)")
    code, body = http_get("/opportunities")
    assert code == 200, f"Expected HTTP 200, got {code}"
    ok(f"HTTP status: {code}")
    assert "<html" in body.lower(), "Response does not look like HTML"
    ok("Response contains HTML markup")
    return True

def test_api_voc():
    section("Test 5 — GET /api/voc")
    code, body = http_get("/api/voc")
    assert code == 200, f"Expected HTTP 200, got {code}"
    ok(f"HTTP status: {code}")
    data = json.loads(body)
    assert isinstance(data, list), "Response data is not a list"
    ok(f"Successfully retrieved VOC list containing {len(data)} items")
    if len(data) > 0:
        item = data[0]
        assert "text" in item, "Review item is missing text field"
        assert "sentiment" in item, "Review item is missing sentiment field"
        ok(f"Review schema validated (text, sentiment present). Sample text: '{item['text'][:30]}...'")
    return True

def test_voc_page():
    section("Test 6 — GET /voice-of-customer (HTML page)")
    code, body = http_get("/voice-of-customer")
    assert code == 200, f"Expected HTTP 200, got {code}"
    ok(f"HTTP status: {code}")
    assert "<html" in body.lower(), "Response does not look like HTML"
    ok("Response contains HTML markup")
    return True

def test_root_redirect():
    section("Test 7 — GET / (root redirect to /dashboard)")
    code, body = http_get("/")
    assert code in (200, 307, 308), f"Unexpected status {code} for root redirect"
    ok(f"Root route responded with HTTP {code} (redirect/dashboard)")
    return True

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("  PRDE INTEGRATION TEST — Frontend + Backend API (Zepto)")
    print("=" * 60)

    # 1. Pre-flight: dashboard_data.json must exist
    section("Pre-flight Check")
    data_file = os.path.join(PROJECT_ROOT, "data", "dashboard_data.json")
    assert os.path.exists(data_file), f"dashboard_data.json missing at {data_file}"
    ok(f"dashboard_data.json found: {data_file}")

    # 2. Start Next.js dev server
    section("Starting Next.js Dev Server")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    
    # Configure env to target the remote Render backend
    env = os.environ.copy()
    env["BACKEND_URL"] = "https://zepto-ai-powered-review-discovery-engine.onrender.com"
    
    server_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    status(f"  Server process PID: {server_proc.pid}")

    try:
        # 3. Wait for server readiness
        if not wait_for_server():
            fail("Server did not become ready within timeout. Aborting.")
            server_proc.terminate()
            sys.exit(1)

        # 4. Run all tests
        tests = [
            test_api_dashboard,
            test_dashboard_page,
            test_pulse_note_page,
            test_opportunities_page,
            test_api_voc,
            test_voc_page,
            test_root_redirect,
        ]

        passed = 0
        failed_tests = []
        for test_fn in tests:
            try:
                test_fn()
                passed += 1
            except Exception as e:
                fail(f"Test '{test_fn.__name__}' FAILED: {e}")
                failed_tests.append(test_fn.__name__)

        # 5. Summary
        print(f"\n{'=' * 60}")
        total = len(tests)
        if not failed_tests:
            print(f"  ✅  ALL {total}/{total} INTEGRATION TESTS PASSED")
        else:
            print(f"  ❌  {len(failed_tests)}/{total} TESTS FAILED: {', '.join(failed_tests)}")
        print("=" * 60)

        sys.exit(0 if not failed_tests else 1)

    finally:
        # Always terminate the dev server
        section("Shutting Down Dev Server")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        ok("Server stopped.")

if __name__ == "__main__":
    main()
