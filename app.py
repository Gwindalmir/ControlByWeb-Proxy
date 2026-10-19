import os
import time
from xml.etree import ElementTree as ET

import requests
from flask import Flask, Response, jsonify, render_template_string

app = Flask(__name__)

DEVICE_BASE_URL = os.getenv("DEVICE_BASE_URL", "http://webrelay.local")
CAMERA_URL = os.getenv("CAMERA_URL", "http://localhost/snapshot.jpg")
RELAY_NUMBER = int(os.getenv("RELAY_NUMBER", "1"))
REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS", "5"))

HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <title>Garage Relay</title>
    <style>
      :root {
        --bg: #111827;
        --panel: #1f2937;
        --panel-2: #374151;
        --text: #f9fafb;
        --muted: #cbd5e1;
        --on: #22c55e;
        --off: #ef4444;
        --accent: #60a5fa;
      }
      * { box-sizing: border-box; }
      html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        min-height: 100%;
        height: 100%;
        overflow: hidden;
        background: linear-gradient(180deg, #0f172a 0%, var(--bg) 100%);
        color: var(--text);
        font-family: Arial, Helvetica, sans-serif;
      }
      body {
        min-height: 100vh;
        max-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        overscroll-behavior: none;
      }
      .shell {
        width: min(100%, 520px);
        height: 100vh;
        max-height: 100vh;
        background: rgba(31, 41, 55, 0.96);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 0;
        box-shadow: none;
        overflow: hidden;
      }
      .header {
        padding: 18px 18px 12px;
        text-align: center;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
      }
      .title {
        margin: 0;
        font-size: clamp(1.5rem, 4vw, 2.1rem);
        font-weight: 700;
      }
      .status-wrap {
        padding: 16px 18px 4px;
      }
      .status-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        padding: 18px 16px;
        border-radius: 14px;
        background: var(--panel-2);
      }
      .label {
        font-size: 0.9rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }
      .value {
        font-size: clamp(1.7rem, 6vw, 2.6rem);
        font-weight: 700;
      }
      .value.closed { color: var(--on); }
      .value.open { color: var(--off); }
      .actions {
        padding: 18px;
      }
      .pulse-btn {
        width: 100%;
        border: 0;
        border-radius: 12px;
        padding: 18px 14px;
        background: linear-gradient(180deg, #3b82f6, #2563eb);
        color: white;
        font-size: 1.1rem;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 10px 18px rgba(37, 99, 235, 0.35);
      }
      .pulse-btn:active {
        transform: scale(0.99);
      }
      .pulse-btn:disabled {
        opacity: 0.6;
        cursor: wait;
      }
      .camera-panel {
        margin: 0 18px 18px;
        border-radius: 14px;
        background: var(--panel-2);
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.14);
      }
      .camera-header {
        padding: 10px 14px;
        font-size: 0.8rem;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: var(--muted);
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
      }
      .camera {
        width: 100%;
        display: block;
        max-height: 42vh;
        object-fit: contain;
        background: #0f172a;
      }
      .error {
        padding: 8px 18px 0;
        color: #fca5a5;
        font-size: 0.9rem;
        min-height: 20px;
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <header class="header">
        <h1 class="title">Garage Relay</h1>
      </header>

      <section class="status-wrap">
        <div class="status-card">
          <div>
            <div class="label">Door</div>
            <div id="statusText" class="value open">OPEN</div>
          </div>
          <div class="label" id="statusBadge">OPEN</div>
        </div>
      </section>

      <div class="error" id="errorBox"></div>

      <div class="actions">
        <button class="pulse-btn" id="pulseButton" type="button">Trigger Door</button>
      </div>

      <section class="camera-panel" aria-label="Garage camera snapshot">
        <div class="camera-header">Live camera</div>
        <img id="cameraImage" class="camera" src="/api/camera/latest.jpg?t=0" alt="Garage camera snapshot" />
      </section>
    </main>

    <script>
      const statusText = document.getElementById('statusText');
      const statusBadge = document.getElementById('statusBadge');
      const pulseButton = document.getElementById('pulseButton');
      const errorBox = document.getElementById('errorBox');
      const cameraImage = document.getElementById('cameraImage');
      const refreshSeconds = {{ refresh_seconds }};

      function setError(message) {
        errorBox.textContent = message || '';
      }

      function updateStatus(data) {
        const closed = Number(data.state) === 1;
        statusText.textContent = closed ? 'CLOSED' : 'OPEN';
        statusText.classList.toggle('closed', closed);
        statusText.classList.toggle('open', !closed);
        statusBadge.textContent = closed ? 'CLOSED' : 'OPEN';
      }

      async function fetchRelay() {
        try {
          const response = await fetch('/api/relay');
          if (!response.ok) {
            throw new Error('Could not read relay state');
          }
          const data = await response.json();
          setError('');
          updateStatus(data);
        } catch (error) {
          setError('Relay unavailable: ' + error.message);
        }
      }

      async function pulseRelay() {
        pulseButton.disabled = true;
        try {
          const response = await fetch('/api/relay/pulse', { method: 'POST' });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.error || 'Pulse failed');
          }
          setError('');
          setTimeout(fetchRelay, 300);
        } catch (error) {
          setError('Pulse failed: ' + error.message);
        } finally {
          setTimeout(() => { pulseButton.disabled = false; }, 700);
        }
      }

      function refreshCamera() {
        cameraImage.src = '/api/camera/latest.jpg?t=' + Date.now();
      }

      pulseButton.addEventListener('click', pulseRelay);
      fetchRelay();
      refreshCamera();
      setInterval(fetchRelay, refreshSeconds * 1000);
      setInterval(refreshCamera, refreshSeconds * 1000);
    </script>
  </body>
</html>
"""


def device_url(path: str) -> str:
    return f"{DEVICE_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def get_input_state() -> int:
    response = requests.get(device_url("state.xml"), timeout=5)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    input_value = root.findtext("input1state")
    if input_value is None:
        raise ValueError("input1state not found in XML response")
    return int(input_value)


def get_relay_state() -> int:
    response = requests.get(device_url("state.xml"), timeout=5)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    relay_value = root.findtext(f"relay{RELAY_NUMBER}state")
    if relay_value is None:
        raise ValueError(f"relay{RELAY_NUMBER}state not found in XML response")
    return int(relay_value)


def fetch_camera_image() -> bytes:
    response = requests.get(CAMERA_URL, timeout=10)
    response.raise_for_status()
    return response.content


@app.get("/health")
def health():
    return jsonify({"status": "ok", "device": DEVICE_BASE_URL, "camera": CAMERA_URL})


@app.get("/api/relay")
def relay_status():
    try:
        state = get_input_state()
        return jsonify({
            "sensor": "input1",
            "state": state,
            "door": "closed" if state else "open",
            "state_text": "CLOSED" if state else "OPEN",
            "relay": RELAY_NUMBER,
        })
    except requests.RequestException as exc:
        return jsonify({"error": f"Device request failed: {exc}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Unable to read door state: {exc}"}), 500


@app.post("/api/relay/pulse")
def pulse_relay():
    try:
        pulse_url = f"{device_url('state.xml')}?relay{RELAY_NUMBER}State=2&time={int(time.time() * 1000)}"
        response = requests.get(pulse_url, timeout=5)
        response.raise_for_status()
        state = get_relay_state()
        return jsonify({"relay": RELAY_NUMBER, "triggered": True, "state": state, "state_text": "ON" if state else "OFF"})
    except requests.RequestException as exc:
        return jsonify({"error": f"Pulse request failed: {exc}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Unable to trigger relay: {exc}"}), 500


@app.get("/api/camera/latest.jpg")
def camera_snapshot():
    try:
        image_bytes = fetch_camera_image()
        return Response(image_bytes, mimetype="image/jpeg", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
    except requests.RequestException as exc:
        return jsonify({"error": f"Camera request failed: {exc}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Unable to fetch camera image: {exc}"}), 500


@app.route("/")
def index():
    return render_template_string(HTML, camera_url="/api/camera/latest.jpg", refresh_seconds=REFRESH_SECONDS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=False)
