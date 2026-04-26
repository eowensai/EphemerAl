#!/usr/bin/env python3
"""Run a lightweight Streamlit UI smoke test and capture screenshots."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

HOST = "127.0.0.1"
PORT = 8501
BASE_URL = f"http://{HOST}:{PORT}"
ARTIFACTS_DIR = Path("artifacts/ui-smoke")
DESKTOP_SCREENSHOT = ARTIFACTS_DIR / "home-desktop.png"
MOBILE_SCREENSHOT = ARTIFACTS_DIR / "home-mobile.png"
STARTUP_TIMEOUT_SECONDS = 90

EXPECTED_WELCOME_TEXT = "Attach files, not just prompts"


class SmokeTestError(RuntimeError):
    """Raised when the smoke test fails for a known reason."""


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _wait_for_http_ready(url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Optional[str] = None

    while time.time() < deadline:
        if STREAMLIT_PROCESS is not None and STREAMLIT_PROCESS.poll() is not None:
            raise SmokeTestError("Streamlit exited before the app became reachable.")
        if _is_port_open(HOST, PORT):
            try:
                with urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 500:
                        return
            except URLError as exc:
                last_error = str(exc)
        time.sleep(0.5)

    detail = f" Last error: {last_error}" if last_error else ""
    raise SmokeTestError(
        f"Streamlit app did not become reachable at {url} within {timeout_seconds}s.{detail}"
    )


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _start_streamlit() -> subprocess.Popen[str]:
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "ephemeral_app.py",
        "--server.headless=true",
        f"--server.address={HOST}",
        f"--server.port={PORT}",
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )


STREAMLIT_PROCESS: Optional[subprocess.Popen[str]] = None


def _capture_ui_screenshots() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            desktop = browser.new_context(viewport={"width": 1440, "height": 900})
            desktop_page = desktop.new_page()
            desktop_page.goto(BASE_URL, wait_until="networkidle", timeout=45_000)

            desktop_page.wait_for_selector("section.welcome-shell", timeout=15_000)
            page_text = desktop_page.content()
            if EXPECTED_WELCOME_TEXT not in page_text and "Welcome to" not in page_text:
                raise SmokeTestError(f"Expected welcome text not found: '{EXPECTED_WELCOME_TEXT}'.")

            if desktop_page.locator('[data-testid="stChatInput"]').count() == 0:
                raise SmokeTestError(
                    "Expected chat input UI element not found. Could not locate Streamlit chat input container."
                )

            desktop_page.screenshot(path=str(DESKTOP_SCREENSHOT), full_page=True)
            desktop.close()

            mobile = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
            )
            mobile_page = mobile.new_page()
            mobile_page.goto(BASE_URL, wait_until="networkidle", timeout=45_000)
            mobile_page.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
            mobile.close()
            browser.close()
    except PlaywrightError as exc:
        raise SmokeTestError(
            "Playwright failed to launch Chromium or interact with the page. "
            "Ensure Playwright + Chromium are installed in this environment."
        ) from exc


def main() -> int:
    global STREAMLIT_PROCESS
    proc = _start_streamlit()
    STREAMLIT_PROCESS = proc

    try:
        _wait_for_http_ready(BASE_URL, STARTUP_TIMEOUT_SECONDS)
        _capture_ui_screenshots()
    except SmokeTestError as exc:
        _terminate_process(proc)
        output = ""
        if proc.stdout:
            try:
                output = proc.stdout.read()
            except Exception:
                output = ""
        message = f"UI smoke test failed: {exc}"
        if output.strip():
            message += f"\n\nCaptured Streamlit output:\n{output[-4000:]}"
        print(message, file=sys.stderr)
        return 1
    finally:
        _terminate_process(proc)

    print("UI smoke test passed.")
    print(f"Desktop screenshot: {DESKTOP_SCREENSHOT}")
    print(f"Mobile screenshot: {MOBILE_SCREENSHOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
