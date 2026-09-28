# API Reference

Base URL: `http://<host>:8000` (WebSockets: `ws://<host>:8000`).

CORS is open to every origin, method and header. There is no authentication.

## HTTP

HTTP responses are wrapped in an envelope. `status` is always `200`; the actual HTTP status code is also 200.

```json
{ "status": 200, "payload": ... }
```

### `GET /ping`

Health check.

```json
{ "status": 200, "payload": { "message": "pong" } }
```

### `GET /sensors`

The latest value of every sensor received so far. The keys are whatever sensor names arrived over MQTT (see [mqtt-ingest.md](mqtt-ingest.md)). Empty until the first MQTT message.

```json
{ "status": 200, "payload": { "temperature": 22.4, "humidity": 61, "ph": 5.9 } }
```

### `GET /sensors/{sensor_name}`

The latest value of one sensor. An unknown or not-yet-received sensor returns `"value": null`, not a 404.

```json
{ "status": 200, "payload": { "sensor": "temperature", "value": 22.4 } }
```

### `GET /command`

The latest command state. See [Limitations](#limitations): this is currently always empty.

```json
{ "status": 200, "payload": {} }
```

## WebSockets

All WebSockets are **server-push only**. After the connection is accepted, the server sends one JSON message every **0.5 s** until the client disconnects. Messages sent by the client are ignored. WebSocket messages are **not** wrapped in the `status`/`payload` envelope.

### `/ws/sensors`

Every sensor, same shape as the `payload` of `GET /sensors`:

```json
{ "temperature": 22.4, "humidity": 61, "ph": 5.9 }
```

### `/ws/sensors/{sensor_name}`

One sensor:

```json
{ "sensor": "temperature", "value": 22.4 }
```

`value` is `null` until the first reading for that sensor arrives.

The dashboard uses these sensor names: `soil`, `temperature`, `humidity`, `ec`, `ph`, `h2o`, `pressure`. The backend doesn't check the name: it looks up whatever key is in the path.

### `/ws/camera`

The camera stream's measured frame rate:

```json
{ "fps": 29.9 }
```

| `fps` value | Meaning |
|---|---|
| `null` | Not measured yet: the backend just started and the first 2-second window hasn't finished |
| `0.0` | The stream is unreachable (MediaMTX or ffmpeg down, camera unplugged). The backend retries every 2 s |
| number | Frames received per second, averaged over the last 2 seconds, one decimal place |

How the value is measured is described in [video-streaming.md](video-streaming.md).

## Camera stream (MediaMTX)

The video itself is not served by the API. Clients connect to MediaMTX directly:

| Protocol | URL | Typical client |
|---|---|---|
| RTSP | `rtsp://<host>:8554/stream` | VLC, ffplay, the backend's fps monitor |
| WebRTC (WHEP) | `http://<host>:8889/stream/whep` | Browsers |
| WebRTC player page | `http://<host>:8889/stream` | Quick check in a browser |

## Limitations

- **`/command` is always empty.** The MQTT handler has a branch for a command topic, but that topic isn't configured or subscribed to (see [mqtt-ingest.md](mqtt-ingest.md#limitations)).
- **No authentication.** Anyone who can reach port 8000 can read all data.
- **`/ws/sensors` swallows all errors.** Its handler uses a bare `except:`, so a bug in it looks like a normal disconnect. The other WebSocket handlers only catch `WebSocketDisconnect`.
