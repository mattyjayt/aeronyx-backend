import os
from dotenv import load_dotenv
from websockets.sync.client import connect

load_dotenv()

def main():
    uri = os.getenv("WS_SENSOR_ENDPOINT")
    with connect(uri) as websocket:
        print(f"Websocket data received: {websocket.recv()}")

if __name__ == "__main__":
    main()