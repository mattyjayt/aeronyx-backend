from src.aeronyx_backend.mqtt_server import MQTTServer
from src.aeronyx_backend.camera_stats import CameraStats
from src.aeronyx_backend.sensor_db import get_sensor_data, get_command_data, get_sensor_value
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"]
)

mqtt_server = MQTTServer()
camera_stats = CameraStats()

@app.get("/ping")
async def ping():
    return {
        "status": 200,
        "payload": {
            "message": "pong"
        }
    }

@app.get("/sensors")
async def sensor_data():
    return {
        "status": 200,
        "payload": get_sensor_data()
    }

@app.get("/sensors/{sensor_name}")
async def sensor_data(sensor_name: str):
    return {
        "status": 200,
        "payload": {"sensor": sensor_name, "value": get_sensor_value(sensor_name)}
    }

@app.get("/command")
async def command():
    return {
        "status": 200,
        "payload": get_command_data()
    }

@app.websocket("/ws/sensors")
async def ws_sensors_general(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(get_sensor_data())
            await asyncio.sleep(0.5)
    except:
        pass

@app.websocket("/ws/sensors/{sensor_name}")
async def ws_sensor_endpoint(ws: WebSocket, sensor_name: str):
    await ws.accept()
    try:
        while True:
            await ws.send_json({"sensor": sensor_name, "value": get_sensor_value(sensor_name)})
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/camera")
async def ws_camera(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({"fps": camera_stats.fps})
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

@app.on_event("startup")
async def startup_event():
    await mqtt_server.start()
    await camera_stats.start()

@app.on_event("shutdown")
async def shutdown_event():
    await camera_stats.stop()
    await mqtt_server.stop()