# Dummy Vehicle Control Panel Simulation

A Python-based graphical user interface (GUI) that simulates a vehicle control panel with real-time data visualization and interactive controls. This simulation is designed for testing, demonstration, and educational purposes.

Hosted on GitHub under [`Yusra412/Dummy-Vehicle-Control-Panel-Simulation-`](https://github.com/Yusra412/Dummy-Vehicle-Control-Panel-Simulation-), the project adheres to modern development practices with modular design, logging, and responsive behavior.

---

## Features

- **Real-Time Simulation**  
  Simulates dummy values for all fields with periodic auto-refresh (every 1–2 seconds).

- **Responsive UI**  
  Layout adjusts dynamically to window resizing while maintaining proper proportions.

- **Interactive Controls**  
  - Gear Selection: `P`, `R`, `N`, `D`, `L`  
  - Maneuver Buttons: `Straight Line`, `Left Turn`, `Right Turn`  
  - Visual feedback on active selections

- **Configurable Start**  
  Loads initial configuration from `config.json` or `config.yaml`.

- **Value Color Coding**  
  Color indicators for value ranges: **Normal**, **Warning**, **Danger**.

- **Debug Mode**  
  Toggle to show additional internal system information.

- **Logging System**  
  Logs in `debug`, `info`, `warning`, and `error` levels.

---

##  Technologies Used

- **Language**: Python 3.8+
- **Libraries**:
  - `tkinter` (for GUI)
  - `pytest` (for unit testing)
- **Coding Standards**:
  - PEP 8 compliant
  - Type hints on all functions
  - Proper docstrings for all classes, functions, and modules

---

##  Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Yusra412/Dummy-Vehicle-Control-Panel-Simulation-.git
cd Dummy-Vehicle-Control-Panel-Simulation-
