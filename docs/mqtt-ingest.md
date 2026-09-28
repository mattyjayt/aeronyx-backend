# MQTT Ingest

Sensor readings reach the backend through an MQTT broker. The sensor hardware publishes to the broker; the backend subscribes and keeps the latest value of each sensor in memory.

## Connection

`MQTTServer` (`src/aeronyx_backend/mqtt_server.py`) wraps a `paho-mqtt` client:

| Setting | Value |
|---|---|
| Broker, port, credentials | From `.env` (see [configuration.md](configuration.md)) |
| TLS | Always on (`tls_set(tls_version=PROTOCOL_TLS)`), using the system CA bundle |
| Keep-alive | 60 s |
| Network loop | `loop_start()`: paho runs its own background thread |

When the connection is accepted (`rc == 0`), the client subscribes to `MQTT_SENSOR_TOPIC`. Otherwise it logs the return code and disconnects.

`start()` calls `connect()` synchronously, so if the broker can't be reached at startup, the exception stops the app from starting.

## Message format

Messages on `MQTT_SENSOR_TOPIC` must be a **UTF-8 JSON object** mapping sensor names to numeric values:

```json
{ "temperature": 22.4, "humidity": 61, "ph": 5.92 }
```

Each message is **merged** into the store (`dict.update`):

- A sensor in the message replaces its previous value.
- A sensor not in the message keeps its previous value.
- A message may contain one sensor or all of them.

A payload that isn't valid JSON is logged and ignored. The values aren't validated: whatever JSON value arrives is stored and served as-is.

### Sensor names

The names in the message become the keys served by `/sensors` and `/ws/sensors/{name}`. The dashboard expects these names:

| Name | Reading | Unit |
|---|---|---|
| `temperature` | Air temperature | °C |
| `humidity` | Relative humidity | % |
| `ec` | Electrical conductivity | mS/cm |
| `ph` | pH | — |
| `soil` | Soil/root-zone moisture | % |
| `h2o` | Reservoir water level | % |
| `pressure` | Air pressure | hPa |

## Storage

`sensor_db.py` holds two module-level dictionaries:

| Store | Written by | Read by |
|---|---|---|
| `_sensor_db` | `update_sensor_data()` from the MQTT sensor topic | `/sensors`, `/sensors/{name}`, `/ws/sensors`, `/ws/sensors/{name}` |
| `_command_db` | `update_command_data()` from the MQTT command topic | `/command` |

Both are cleared when `mqtt_server.py` is imported and are never written to disk.

## Limitations

- **The command topic doesn't work yet.** `on_message` has a branch for `MQTT_COMMAND_TOPIC`, but that variable is never defined and the topic is never subscribed to. As a result, `/command` is always empty, and if a message ever arrives on a topic other than the sensor topic, the handler raises a `NameError`.
- **`on_connect` is defined twice** in `mqtt_server.py`. The second definition is the one used.
- **`on_disconnect` unsubscribes after the connection is already gone**, so that call has no effect. paho reconnects automatically, and `on_connect` subscribes again.
