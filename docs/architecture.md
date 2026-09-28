# Architecture

## Processes

`backend.sh` starts two long-running processes on the Pi:

| Process | What it does |
|---|---|
| **MediaMTX** (`mediamtx/mediamtx`) | Media server. On startup it launches an `ffmpeg` process that captures `/dev/video0`, encodes H.264, and publishes it to the `stream` path. MediaMTX then serves that path over RTSP, WebRTC and HLS. |
| **Uvicorn** running `main:app` | The FastAPI application: HTTP + WebSocket API, the MQTT client, and the fps monitor. |

The two processes only talk through the network: the API reads the camera stream from MediaMTX over RTSP like any other client.

## Inside the API process

```
                ┌──────────────────────── uvicorn process ─────────────────────────┐
                │                                                                  │
 HiveMQ ──TLS──▶│  paho network thread ──on_message──▶ sensor_db (dicts in memory) │
                │                                              │                   │
                │  asyncio event loop (FastAPI)  ◀── reads ────┘                   │
                │    HTTP routes, WebSocket loops ◀── reads camera_stats.fps       │
                │                                              ▲                   │
 MediaMTX ─RTSP▶│  camera-stats thread (PyAV demux) ── writes ─┘                   │
                └──────────────────────────────────────────────────────────────────┘
```

Three threads of execution share state:

1. **The asyncio event loop** runs every HTTP route and WebSocket handler. Handlers never block: they only read in-memory values and `await asyncio.sleep(...)`.
2. **The paho-mqtt network thread**, started by `MQTTServer.start()` via `loop_start()`. It receives MQTT messages and writes them into `sensor_db`.
3. **The `camera-stats` thread**, started by `CameraStats.start()`. It reads the RTSP stream and updates `CameraStats.fps`.

Shared state is kept deliberately simple: plain dictionaries and a single float. Writes are single operations (`dict.update`, attribute assignment), which are atomic under CPython's GIL, so no locks are used. Readers get a copy (`dict.copy()`) so they never see a dictionary change while iterating it.

## Modules

| Module | Responsibility |
|---|---|
| `main.py` | Creates the FastAPI app, enables CORS for all origins, defines routes, and starts/stops the background services in the `startup`/`shutdown` events. |
| `src/aeronyx_backend/mqtt_server.py` | `MQTTServer`: connects to the broker over TLS, subscribes to the sensor topic, and forwards JSON payloads to `sensor_db`. See [mqtt-ingest.md](mqtt-ingest.md). |
| `src/aeronyx_backend/sensor_db.py` | In-memory store: `_sensor_db` (sensor name → latest value) and `_command_db` (command name → latest value). Getters return copies. |
| `src/aeronyx_backend/camera_stats.py` | `CameraStats`: background thread that counts video packets and computes a rolling fps. See [video-streaming.md](video-streaming.md). |

## Lifecycle

On **startup** (`@app.on_event("startup")`):

1. `mqtt_server.start()` connects to the broker and starts the network thread.
2. `camera_stats.start()` starts the fps thread. If MediaMTX isn't ready yet, the thread simply retries every 2 s.

Importing `mqtt_server.py` also loads `.env` and clears the sensor store. This happens at import time, before startup.

On **shutdown**:

1. `camera_stats.stop()` sets a stop flag and waits up to 3 s for the thread to exit.
2. `mqtt_server.stop()` stops the network thread and disconnects.

## Data persistence

Nothing is persisted. The sensor and command stores live in process memory and are empty after every restart until new MQTT messages arrive. With `uvicorn --reload` (used by `backend.sh`), saving a Python file restarts the process and clears them too.

## Design notes

- **Push model.** WebSocket handlers push the current state every 0.5 s whether or not it changed. Clients never need to send anything; the handlers don't read incoming messages.
- **One stream reader, many viewers.** The fps monitor opens the camera stream once, no matter how many clients are connected to `/ws/camera`. Each WebSocket just reads the latest number.
- **No decoding.** The Pi 5 has no hardware H.264 decoder, so the fps monitor counts compressed packets instead of decoding frames. This keeps its CPU cost close to zero.
