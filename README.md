# ControlByWeb Relay Mobile Wrapper

A lightweight mobile-first Flask wrapper for a ControlByWeb X-301 device on the local network. It shows the current status for relay 1, includes a large pulse button to trigger the relay, and refreshes a camera snapshot every 5 seconds.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8080

## Docker

```bash
docker build -t controlbyweb-relay .
```

For a Linux host with LAN name resolution:

```bash
docker run --rm --network host \
  -e DEVICE_BASE_URL=http://webrelay.local \
  -e CAMERA_URL=http://IP:PORT/snapshot.jpg \
  controlbyweb-relay
```

The app listens on port 8080 and is designed for mobile screens.

## Device protocol notes

This wrapper uses the ControlByWeb XML endpoint:

- Read state: `http://webrelay.local/state.xml`
- Trigger relay 1 pulse: `http://webrelay.local/state.xml?relay1State=2`

The HTML page on the device shows that `relay1State=2` is the pulse action and `relay1state` in the XML response is the current value (`0` or `1`).

## Disclaimer

I used Copilot to help build this quickly.