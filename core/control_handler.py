import logging
import time
import random
from typing import Dict, Any
from core.data_loader import VehicleData

logger = logging.getLogger(__name__)

class ControlHandler:
    """Handles vehicle controls, simulation, and data management."""
    def __init__(self, vehicle_data: VehicleData, simulation_enabled: bool):
        self.vehicle_data = vehicle_data
        self.simulation_enabled = simulation_enabled
        self.is_running = True
        self.is_paused = False
        self._last_update_time = time.time()
        # Placeholder for maneuver presets (not implemented in provided code)
        self.all_maneuver_presets = {
            "Standard Cruise": {"speed_kmh": 60, "steering_wheel_angle": 0},
            "Sharp Turn": {"steering_wheel_angle": 300, "speed_kmh": 30},
            "Emergency Stop": {"break_value": 100, "speed_kmh": 0}
        }
        logger.info("ControlHandler initialized.")

    def simulate_vehicle_data(self) -> None:
        """Simulates dynamic changes in vehicle data."""
        if not self.simulation_enabled or not self.is_running or self.is_paused:
            return

        current_time = time.time()
        delta_time = current_time - self._last_update_time
        self._last_update_time = current_time

        if self.vehicle_data.vehicle_started:
            # RPM simulation
            if self.vehicle_data.accel_value > 0:
                self.vehicle_data.rpm = min(8000, self.vehicle_data.rpm + self.vehicle_data.accel_value * 5 * delta_time)
            elif self.vehicle_data.break_value > 0:
                self.vehicle_data.rpm = max(0, self.vehicle_data.rpm - self.vehicle_data.break_value * 2 * delta_time)
            else:
                self.vehicle_data.rpm = max(0, self.vehicle_data.rpm - 100 * delta_time)
            self.vehicle_data.rpm = round(self.vehicle_data.rpm, 0)

            # Speed simulation
            driving_gears = ["D", "R", "L", "1", "2", "3", "4", "5", "6"]
            if self.vehicle_data.maneuver_active:
                # Apply maneuver preset if active
                preset = self.all_maneuver_presets.get(self.vehicle_data.maneuver_name, {})
                if preset:
                    self.vehicle_data.speed_kmh = preset.get("speed_kmh", self.vehicle_data.speed_kmh)
                    self.vehicle_data.steering_wheel_angle = preset.get("steering_wheel_angle", self.vehicle_data.steering_wheel_angle)
                    self.vehicle_data.break_value = preset.get("break_value", self.vehicle_data.break_value)
            elif self.vehicle_data.accel_value > 0 and self.vehicle_data.break_value == 0 and self.vehicle_data.gear in driving_gears:
                self.vehicle_data.speed_kmh = min(300, self.vehicle_data.speed_kmh + (self.vehicle_data.accel_value / 10) * delta_time * 5)
            elif self.vehicle_data.break_value > 0:
                self.vehicle_data.speed_kmh = max(0, self.vehicle_data.speed_kmh - (self.vehicle_data.break_value / 5) * delta_time * 5)
            else:
                if self.vehicle_data.gear in driving_gears and self.vehicle_data.speed_kmh > 0:
                    self.vehicle_data.speed_kmh = max(0, self.vehicle_data.speed_kmh - 5 * delta_time)
                elif self.vehicle_data.gear in ["N", "P"]:
                    self.vehicle_data.speed_kmh = 0.0
            self.vehicle_data.speed_kmh = round(self.vehicle_data.speed_kmh, 1)

            # Odometer
            if self.vehicle_data.speed_kmh > 0:
                self.vehicle_data.odometer_km += (self.vehicle_data.speed_kmh / 3600) * delta_time
                self.vehicle_data.odometer_km = round(self.vehicle_data.odometer_km, 3)

            # Position and angles
            self.vehicle_data.pos_x_m = round(self.vehicle_data.pos_x_m + random.uniform(-0.05, 0.05), 3)
            self.vehicle_data.pos_y_m = round(self.vehicle_data.pos_y_m + random.uniform(-0.05, 0.05), 3)
            self.vehicle_data.pos_z_m = round(self.vehicle_data.pos_z_m + random.uniform(-0.05, 0.05), 3)
            self.vehicle_data.angle_roll_deg = round(random.uniform(-5, 5), 1)
            self.vehicle_data.angle_pitch_deg = round(random.uniform(-5, 5), 1)
            self.vehicle_data.angle_yaw_deg = round(random.uniform(-180, 180), 1)

            # Rates
            self.vehicle_data.roll_rate_degs = round(23.40 + random.uniform(-1, 1), 1)
            self.vehicle_data.pitch_rate_degs = round(23.40 + random.uniform(-1, 1), 1)
            self.vehicle_data.yaw_rate_degs = round(166.7 + random.uniform(-10, 10), 1)

        # Ensure values stay within limits
        self.vehicle_data.rpm = max(0, min(8000, self.vehicle_data.rpm))
        self.vehicle_data.speed_kmh = max(0, min(300, self.vehicle_data.speed_kmh))
        self.vehicle_data.clutch_value = max(0, min(100, self.vehicle_data.clutch_value))
        self.vehicle_data.break_value = max(0, min(100, self.vehicle_data.break_value))
        self.vehicle_data.accel_value = max(0, min(100, self.vehicle_data.accel_value))
        self.vehicle_data.steering_wheel_angle = max(-780, min(780, self.vehicle_data.steering_wheel_angle))

        logger.debug("Vehicle data simulated.")

    def set_gear(self, gear: str) -> None:
        """Sets the vehicle's gear."""
        if self.vehicle_data.vehicle_started or gear in ['P', 'N']:
            self.vehicle_data.gear = gear
            logger.info(f"Gear set to: {gear}.")
        else:
            logger.warning(f"Cannot set gear {gear}: Vehicle is off.")

    def start_maneuver(self, maneuver_name: str = None) -> None:
        """Starts a simulated maneuver."""
        if self.vehicle_data.vehicle_started:
            self.vehicle_data.maneuver_active = True
            self.vehicle_data.maneuver_name = maneuver_name
            logger.info(f"Maneuver started: {maneuver_name}")
        else:
            logger.warning("Cannot start maneuver: Vehicle is off.")

    def stop_maneuver(self) -> None:
        """Stops a simulated maneuver."""
        self.vehicle_data.maneuver_active = False
        self.vehicle_data.maneuver_name = None
        logger.info("Maneuver stopped.")

    def reset_vehicle(self, initial_data_dict: Dict[str, Any]) -> None:
        """Resets all vehicle parameters to their initial state."""
        for key, value in initial_data_dict.items():
            setattr(self.vehicle_data, key, value)
        self.vehicle_data.vehicle_started = False
        self.vehicle_data.maneuver_active = False
        self.vehicle_data.maneuver_name = None
        self.is_running = True

        self.is_paused = False
        self._last_update_time = time.time()
        logger.info("Vehicle reset performed.")

    def toggle_pause(self) -> None:
        """Toggles the simulation pause state."""
        self.is_paused = not self.is_paused
        logger.info(f"Simulation {'paused' if self.is_paused else 'resumed'}.")

    def stop_simulation(self) -> None:
        """Stops the entire simulation."""
        self.is_running = False
        self.is_paused = False
        self.vehicle_data.vehicle_started = False
        self.vehicle_data.rpm = 0.0
        self.vehicle_data.speed_kmh = 0.0
        self.vehicle_data.gear = "P"
        logger.info("Simulation stopped.")

    def set_clutch_value(self, value: float) -> None:
        self.vehicle_data.clutch_value = value
        logger.debug(f"Clutch set to: {value}")

    def set_break_value(self, value: float) -> None:
        self.vehicle_data.break_value = value
        logger.debug(f"Break set to: {value}")

    def set_accel_value(self, value: float) -> None:
        self.vehicle_data.accel_value = value
        logger.debug(f"Accel set to: {value}")

    def set_steering_wheel_angle(self, angle: float) -> None:
        self.vehicle_data.steering_wheel_angle = angle
        logger.debug(f"Steering angle set to: {angle}")

    def toggle_vehicle_power(self) -> None:
        """Toggles the vehicle's engine on/off."""
        self.vehicle_data.vehicle_started = not self.vehicle_data.vehicle_started
        if not self.vehicle_data.vehicle_started:
            self.vehicle_data.rpm = 0.0
            self.vehicle_data.speed_kmh = 0.0
            self.vehicle_data.gear = "P"
        logger.info(f"Vehicle power toggled to: {'ON' if self.vehicle_data.vehicle_started else 'OFF'}.")