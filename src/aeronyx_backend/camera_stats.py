import os
import time
import threading
from collections import deque
import av
from dotenv import load_dotenv

load_dotenv()

CAMERA_RTSP_URL     = os.getenv("CAMERA_RTSP_URL", "rtsp://localhost:8554/stream")
FPS_WINDOW          = 2.0   # seconds of packet history used to compute fps
OPEN_TIMEOUT        = 5.0   # seconds to wait when connecting to the stream
READ_TIMEOUT        = 2.0   # seconds to wait for the next packet
RECONNECT_DELAY     = 2.0   # seconds to wait before reconnecting after a failure


class CameraStats:
    def __init__(self, url=None):
        self.url        = url or CAMERA_RTSP_URL
        self.fps        = None
        self._stop      = threading.Event()
        self._thread    = None

    async def start(self):
        # Start the stream reader thread
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="camera-stats", daemon=True)
        self._thread.start()

    async def stop(self):
        # Stop the stream reader thread
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=READ_TIMEOUT + 1)

    def _run(self):
        while not self._stop.is_set():
            container = None
            try:
                container = av.open(
                    self.url,
                    options={"rtsp_transport": "tcp"},
                    timeout=(OPEN_TIMEOUT, READ_TIMEOUT),
                )
                print(f"[CAMERA] Connected to {self.url}")
                self._count_packets(container)
            except (av.error.FFmpegError, OSError) as e:
                print(f"[CAMERA] Stream unavailable: {e}")
            finally:
                # Stream is down (or we're shutting down): report no frames
                self.fps = 0.0
                if container:
                    container.close()
            self._stop.wait(RECONNECT_DELAY)

    def _count_packets(self, container):
        video_stream    = container.streams.video[0]
        arrivals        = deque()
        connected_at    = time.monotonic()

        for packet in container.demux(video_stream):
            if self._stop.is_set():
                break
            # Flush packets at end of stream carry no data
            if packet.size == 0:
                continue

            now = time.monotonic()
            arrivals.append(now)
            while arrivals and arrivals[0] < now - FPS_WINDOW:
                arrivals.popleft()

            # Skip the first window: the backlog sent on connect inflates the count
            if now - connected_at >= FPS_WINDOW:
                self.fps = round(len(arrivals) / FPS_WINDOW, 1)
