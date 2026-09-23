from src.aeronyx_backend.mqtt_server import MQTTServer
from src.aeronyx_backend.sensor_db import get_sensor_data, get_command_data
from fastapi import FastAPI, WebSocket, HTTPException
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

@app.get("/ping")
async def ping():
    return {
        "status": 200,
        "payload": {
            "message": "pong"
        }
    }

@app.get("/sensor_data")
async def sensor_data():
    return {
        "status": 200,
        "payload": get_sensor_data()
    }

@app.get("/command")
async def command():
    return {
        "status": 200,
        "payload": get_command_data()
    }

@app.websocket("/ws/sensors")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(get_sensor_data())
            await asyncio.sleep(0.5)
    except:
        pass

@app.websocket("/ws/command")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(get_command_data())
            await asyncio.sleep(0.5)
    except:
        pass

@app.on_event("startup")
async def startup_event():
    await mqtt_server.start()

@app.on_event("shutdown")
async def shutdown_event():
    await mqtt_server.stop()