# Video Streaming

```
/dev/video0 ──MJPEG──▶ ffmpeg ──H.264 / RTSP publish──▶ MediaMTX "stream" path
                                                          ├── RTSP  :8554 ──▶ fps monitor (backend), VLC, …
                                                          ├── WebRTC :8889 ──▶ browsers (aeronyx-ui)
                                                          └── HLS   :8888
```

## Capture pipeline

MediaMTX starts `ffmpeg` itself (`runOnInit` in `mediamtx.yml`) and restarts it if it exits (`runOnInitRestart: yes`). The command:

| Option | Why |
|---|---|
| `-f v4l2 -input_format mjpeg` | Read from the USB camera in MJPEG mode, which most USB cameras need to reach 1080p30 |
| `-video_size 1920x1080 -framerate 30` | Request 1080p at 30 fps. The camera may deliver fewer frames, e.g. in low light |
| `-c:v libx264 -preset ultrafast` | Software H.264 encode (the Pi 5 has no hardware H.264 encoder), tuned for the lowest CPU use |
| `-tune zerolatency` | No B-frames and no lookahead, so each frame is sent immediately. This also means one packet = one frame, which the fps monitor relies on |
| `-pix_fmt yuv420p` | The pixel format browsers can decode |
| `-b:v 2M -g 30` | 2 Mbit/s target bitrate; a keyframe every 30 frames (~1 s), so new viewers start quickly |
| `-f rtsp rtsp://localhost:$RTSP_PORT/$MTX_PATH` | Publish back into MediaMTX on this path (`stream`) |

## MediaMTX

MediaMTX receives the published stream once and serves it to any number of clients, converting between protocols without re-encoding. Browsers use WebRTC through the WHEP endpoint `http://<host>:8889/stream/whep`, because browsers can't play RTSP.

MediaMTX writes its logs to `mediamtx/mediamtx.log` (redirected by `backend.sh`).

## FPS measurement

`CameraStats` (`src/aeronyx_backend/camera_stats.py`) measures the frame rate that actually reaches a client, not the rate the stream claims to have.

### How it works

1. A daemon thread named `camera-stats` opens `CAMERA_RTSP_URL` with PyAV, forcing **RTSP over TCP**. Over UDP, dropped packets would show up as a lower fps.
2. It **demuxes** the video stream: it reads compressed H.264 packets without decoding them. Because the encoder uses `zerolatency` (no B-frames), each packet is one frame.
3. Empty packets (`size == 0`, sent when the stream ends) are skipped.
4. Each packet's arrival time (`time.monotonic()`) is added to a queue. Timestamps older than `FPS_WINDOW` (2 s) are removed.
5. `fps = packets in window / FPS_WINDOW`, rounded to one decimal place and stored in `CameraStats.fps`.
6. `/ws/camera` sends that value to every connected client.

### Why arrival time, not stream timestamps

Packet timestamps (`pts`) say when the source intended each frame to be shown. Arrival time says how fast frames are actually reaching you. For a stream health metric, the second is what matters: it drops when the camera, the encoder, or the network falls behind.

### Startup and failures

| Situation | Behaviour | `fps` |
|---|---|---|
| Backend just started | Waits one full window before reporting, because MediaMTX may send a burst of buffered packets on connect | `null` |
| Stream healthy | Updated on every packet | ~30.0 |
| Connection refused, or no packet for 2 s | Error logged as `[CAMERA] Stream unavailable: …`, container closed, retry after 2 s | `0.0` |
| Stream comes back | Reconnects and logs `[CAMERA] Connected to …` | ~30.0 again after one window |

Only PyAV/FFmpeg errors (`av.error.FFmpegError`) and `OSError` are caught. Any other exception ends the thread, which leaves `fps` at its last value.

### Shutdown

`stop()` sets a `threading.Event`. The thread checks it on every packet and during the reconnect wait. The 2 s read timeout means the thread wakes up even when no packets are arriving. `stop()` waits up to 3 s for the thread to finish.

### Cost

No frames are decoded, so the monitor uses almost no CPU: it only receives about 2 Mbit/s over localhost and counts packets.
