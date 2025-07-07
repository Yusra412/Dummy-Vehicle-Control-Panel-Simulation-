import json
import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class VehicleData:
    """Data class for vehicle telemetry, matching GUI usage."""
    rpm: float = 0.0
    speed_kmh: float = 0.0
    odometer_km: float = 0.0
    gear: str = "N"
    pos_x_m: float = 0.0
    pos_y_m: float = 0.0
    pos_z_m: float = 0.0
    angle_roll_deg: float = 0.0
    angle_pitch_deg: float = 0.0
    angle_yaw_deg: float = 0.0
    roll_rate_degs: float = 0.0
    pitch_rate_degs: float = 0.0
    yaw_rate_degs: float = 0.0
    clutch_value: float = 0.0
    break_value: float = 0.0
    accel_value: float = 0.0
    steering_wheel_angle: float = 0.0
    vehicle_started: bool = False
    maneuver_active: bool = False

    def validate(self) -> bool:
        """Validate vehicle data ranges."""
        try:
            return (
                0 <= self.rpm <= 8000 and
                0 <= self.speed_kmh <= 300 and
                -780 <= self.steering_wheel_angle <= 780 and
                0 <= self.clutch_value <= 100 and
                0 <= self.break_value <= 100 and
                0 <= self.accel_value <= 100
            )
        except TypeError as e:
            logger.error(f"Type error during data validation: {e}")
            return False

class ConfigManager:
    """Handles loading and saving configuration from a JSON file."""
    def __init__(self, config_file_path: str = 'data/config.json'):
        self.config_file = config_file_path
        self.default_config: Dict[str, Any] = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Returns a default configuration dictionary."""
        return {
            "refresh_rate": 1000,
            "simulation_enabled": True,
            "debug_mode": False,
            "vehicle_data": {
                "rpm": 1500,
                "speed_kmh": 45.0,
                "odometer_km": 0.0,
                "gear": "N",
                "clutch_value": 0.0,
                "break_value": 0.0,
                "accel_value": 4.6,
                "pos_x_m": 3400.0,
                "pos_y_m": 3400.0,
                "pos_z_m": 3400.0,
                "angle_roll_deg": 0.0,
                "angle_pitch_deg": 0.0,
                "angle_yaw_deg": 0.0,
                "roll_rate_degs": 3.4,
                "pitch_rate_degs": 3.4,
                "yaw_rate_degs": 166.7,
                "steering_wheel_angle": 60.0,
                "vehicle_started": False,
                "maneuver_active": False
            }
        }

    def load_config(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file, or create with defaults if not found."""
        config_file = file_path or self.config_file
        if not os.path.exists(config_file):
            logger.warning(f"Config file {config_file} not found. Creating with default values.")
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            self.save_config(self.default_config)
            return self.default_config

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_file}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file {config_file}: {e}. Using default configuration.")
            return self.default_config
        except Exception as e:
            logger.error(f"Unexpected error loading config from {config_file}: {e}. Using default configuration.")
            return self.default_config

    def save_config(self, config: Dict[str, Any], file_path: Optional[str] = None) -> None:
        """Save configuration to file."""
        config_file = file_path or self.config_file
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration to {config_file}: {e}")