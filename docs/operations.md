# Operations

## Installing

```sh
uv sync         # Python dependencies from pyproject.toml / uv.lock
./install.sh    # MediaMTX
```

`install.sh`:

1. Looks up the latest MediaMTX release through the GitHub API.
2. Downloads the `linux_arm64` build and extracts it into `./mediamtx/`.
3. Saves the stock config as `mediamtx/mediamtx.yml.original`.
4. Writes `mediamtx/mediamtx.yml` with the `stream` path and camera capture command (see [configuration.md](configuration.md#mediamtx-mediamtxmediamtxyml)).

Running it again upgrades MediaMTX to the latest release **and regenerates `mediamtx.yml`**, which discards any manual edits.

`ffmpeg` must be installed separately (e.g. `sudo apt install ffmpeg`).

## Running

```sh
./backend.sh
```

`backend.sh`:

1. Kills any MediaMTX or Uvicorn left over from a previous run.
2. Checks that the MediaMTX binary, its config, and `uv` exist.
3. Starts MediaMTX in the background, logging to `mediamtx/mediamtx.log`.
4. Starts `uv run uvicorn main:app --reload --host 0.0.0.0` in the foreground (port 8000).

Press **Ctrl+C** to stop. An exit trap stops MediaMTX, which also stops the ffmpeg capture process it started.

`--reload` restarts the API whenever a Python file changes. That's convenient during development, but it also clears the in-memory sensor store.

## Logs

| Source | Where |
|---|---|
| API, MQTT (`[MQTT] …`), camera monitor (`[CAMERA] …`) | The terminal running `backend.sh` |
| MediaMTX and the ffmpeg capture | `mediamtx/mediamtx.log` |

## Checking each part

| Check | Command |
|---|---|
| API is up | `curl http://localhost:8000/ping` |
| Sensors are arriving | `curl http://localhost:8000/sensors` |
| Camera stream works | `ffplay rtsp://localhost:8554/stream`, or open `http://<host>:8889/stream` in a browser |
| FPS WebSocket | `websocat ws://localhost:8000/ws/camera` (or `wscat -c ...`) |
| Camera device | `v4l2-ctl --list-devices` and `v4l2-ctl -d /dev/video0 --list-formats-ext` |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| App crashes at startup with `TypeError: int() argument must be ... not 'NoneType'` | `MQTT_PORT` missing from `.env` |
| App fails at startup with a connection or TLS error | Broker unreachable or wrong host/port. `start()` connects synchronously, so this stops startup |
| `/sensors` stays `{}` | Nothing is publishing to `MQTT_SENSOR_TOPIC`, the topic name doesn't match, or the payload isn't a JSON object |
| `fps` stays `0.0` | MediaMTX has no `stream`: check `mediamtx.log` for ffmpeg errors, e.g. camera busy or unsupported format/size |
| `fps` well below 30 | Camera lowering its frame rate (low light), or the Pi is CPU-bound encoding. Check with `htop` |
| `fps` stays `null` | The monitor never received a full window of packets. Check `[CAMERA]` log lines |
| `Device or resource busy` in `mediamtx.log` | Another process holds `/dev/video0`, often an orphaned ffmpeg: `pkill -f "ffmpeg.*video0"` |
| Browser shows no video but RTSP works | WebRTC blocked: port 8889 (TCP) or the MediaMTX WebRTC UDP port (8189 by default) isn't reachable from the client |
