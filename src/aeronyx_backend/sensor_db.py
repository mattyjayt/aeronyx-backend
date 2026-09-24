_sensor_db: dict[str, float] = {}
_command_db: dict[str, str] = {}

def initialize_database() -> None:
    _sensor_db.clear()
    _command_db.clear()

def get_sensor_value(name: str) -> float | None:
    return _sensor_db.get(name) 

def update_sensor_data(sensor_data: dict[str, float]) -> None:
    _sensor_db.update(sensor_data)

def get_sensor_data() -> dict[str, float]:
    return _sensor_db.copy()

def update_command_data(command_data: dict[str, str]) -> None:
    _command_db.update(command_data)

def get_command_data() -> dict[str, str]:
    return _command_db.copy()