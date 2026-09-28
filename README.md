# Aeronyx Backend

The backend for **Aeronyx**, an aeroponics grow-tower controller. It runs on a Raspberry Pi 5 next to the tower and:

- **Receives sensor telemetry** from an MQTT broker (HiveMQ, over TLS) and keeps the latest value of each sensor.
- **Serves that telemetry** over HTTP and WebSockets.
- **Publishes the live camera feed** through [MediaMTX](https://github.com/bluenviron/mediamtx) as RTSP and WebRTC.
- **Measures the stream's real frame rate** and pushes it over a WebSocket.

The operator dashboard is a separate project, **aeronyx-ui**. It connects to the endpoints listed below and plays the camera feed directly from MediaMTX.

```
 sensors ──MQTT──▶ HiveMQ ──TLS──▶ ┌──────────────────┐ ──HTTP / WS──▶ aeronyx-ui
                                   │ FastAPI backend  │
 USB camera ─▶ ffmpeg ─▶ MediaMTX ─RTSP─▶ fps monitor │
                           │       └──────────────────┘
                           └────────── WebRTC (WHEP) ──────────▶ aeronyx-ui
```

## Requirements

- Raspberry Pi 5 (or another Linux arm64 host)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- `ffmpeg` on `PATH`
- A V4L2 camera at `/dev/video0` that can output MJPEG at 1920×1080
- An MQTT broker account (HiveMQ Cloud is used today)

## Quick start

```sh
uv sync          # installs Python dependencies
./install.sh     # downloads MediaMTX into ./mediamtx and writes its config
                 # create .env (see Configuration below)
./backend.sh     # starts MediaMTX and the API; Ctrl+C stops both
```

The API listens on port `8000`. The camera is published at `rtsp://<host>:8554/stream` and `http://<host>:8889/stream/whep`.

## Endpoints

| Endpoint | Type | Returns |
|---|---|---|
| `/ping` | HTTP GET | Health check |
| `/sensors` | HTTP GET | Latest value of every sensor |
| `/sensors/{name}` | HTTP GET | Latest value of one sensor |
| `/command` | HTTP GET | Latest command state |
| `/ws/sensors` | WebSocket | All sensors, pushed every 0.5 s |
| `/ws/sensors/{name}` | WebSocket | One sensor, pushed every 0.5 s |
| `/ws/camera` | WebSocket | Measured camera fps, pushed every 0.5 s |

Payload formats are documented in [docs/api.md](docs/api.md).

## Configuration

Settings are read from `.env` in the project root:

| Variable | Required | Purpose |
|---|---|---|
| `MQTT_BROKER` | yes | Broker hostname |
| `MQTT_PORT` | yes | Broker TLS port (usually `8883`) |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | yes | Broker credentials |
| `MQTT_SENSOR_TOPIC` | yes | Topic that sensor readings are published to |
| `CAMERA_RTSP_URL` | no | Stream the fps monitor reads (default `rtsp://localhost:8554/stream`) |

See [docs/configuration.md](docs/configuration.md) for the full reference, including the camera and MediaMTX settings.

## Project layout

```
main.py                         FastAPI app: routes, WebSockets, startup/shutdown
src/aeronyx_backend/
  mqtt_server.py                MQTT client that feeds the sensor store
  sensor_db.py                  In-memory store of the latest readings
  camera_stats.py               Background fps monitor for the camera stream
install.sh                      Installs and configures MediaMTX
backend.sh                      Runs MediaMTX + the API together
mediamtx/                       MediaMTX binary, config and log (created by install.sh, git-ignored)
docs/                           Technical documentation
```

## Documentation

| Document | Covers |
|---|---|
| [Architecture](docs/architecture.md) | Components, threads, and how data moves through the backend |
| [API reference](docs/api.md) | Every HTTP and WebSocket endpoint, with payloads |
| [Configuration](docs/configuration.md) | Environment variables, MediaMTX, and the camera pipeline settings |
| [MQTT ingest](docs/mqtt-ingest.md) | Broker connection, topics, and the expected message format |
| [Video streaming](docs/video-streaming.md) | Camera capture, MediaMTX, and how fps is measured |
| [Operations](docs/operations.md) | Installing, running, logs, and troubleshooting |
