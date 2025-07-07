import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

from core.data_loader import VehicleData, ConfigManager
from core.control_handler import ControlHandler

logger = logging.getLogger(__name__)

class TextHandler(logging.Handler):
    """Custom logging handler to redirect logs to Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)

class VehicleControlPanel:
    """Main vehicle control panel application."""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vehicle Control Panel Simulation v1.1")
        self.root.geometry("1000x600")  # Reduced window size
        self.root.configure(bg='#2b2b2b')

        # Initialize components with smaller position values
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.config.setdefault("vehicle_data", {}).update({
            "pos_x_m": 0.340,
            "pos_y_m": 0.450,
            "pos_z_m": 0.560
        })
        self.vehicle_data = VehicleData(**self.config.get("vehicle_data", {}))
        self.control_handler = ControlHandler(self.vehicle_data, self.config.get("simulation_enabled", True))
        
        # State variables
        self.debug_mode = self.config.get("debug_mode", False)
        self.warning_visible = True
        self.sim_thread_running = False
        self.widgets = {}
        self.canvases = {}
        self.log_text_widget = None

        # Styling
        self.setup_style()
        
        # Create GUI
        self.create_menu()
        self.create_gui()
        
        # Start simulation thread
        self.start_sim_thread()
        self.update_gui_periodic()

        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger.info("Application initialized.")

    def setup_style(self) -> None:
        """Configures ttk styles for a modern dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', background='#007bff', foreground='#ffffff', font=('Arial', 8, 'bold'), padding=3)
        style.map('TButton', background=[('active', '#0056b3')], foreground=[('active', '#ffffff')])
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='#ffffff', font=('Arial', 8))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'), foreground='#007bff')
        style.configure('Value.TLabel', background='#3c3c3c', foreground='#ffffff', font=('Arial', 12, 'bold'))
        style.configure('TScale', background='#2b2b2b', foreground='#ffffff', troughcolor='#3c3c3c', sliderrelief='flat')
        style.map('TScale', background=[('active', '#6c6c6c')])
        style.configure('TCombobox', fieldbackground='#3c3c3c', background='#3c3c3c', foreground='#ffffff', selectbackground='#007bff', selectforeground='#ffffff', arrowcolor='#ffffff')
        style.map('TCombobox', fieldbackground=[('readonly', '#3c3c3c')], background=[('readonly', '#3c3c3c')])
        style.configure('TCheckbutton', background='#2b2b2b', foreground='#ffffff', font=('Arial', 8))
        style.map('TCheckbutton', background=[('active', '#2b2b2b')])
        self.root.option_add('*tearOff', tk.FALSE)

    def create_menu(self) -> None:
        """Creates the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Configuration", command=self.load_config_dialog)
        file_menu.add_command(label="Save Configuration", command=self.save_config_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        options_menu = tk.Menu(menubar)
        menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_checkbutton(label="Debug Mode", variable=tk.BooleanVar(value=self.debug_mode), command=self.toggle_debug_mode)
        options_menu.add_checkbutton(label="Simulation", command=self.toggle_simulation)
        help_menu = tk.Menu(menubar)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_gui(self) -> None:
        """Creates and lays out all GUI elements."""
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)  # Reduced padding

        # Top panel: Gauges and Odometer
        top_frame = tk.Frame(main_frame, bg='#404040', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        gauge_frame = tk.Frame(top_frame, bg='#404040')
        gauge_frame.pack(side=tk.LEFT, padx=10, pady=10)
        self.canvases['rpm'] = tk.Canvas(gauge_frame, width=150, height=150, bg='black', highlightthickness=0)  # Reduced size
        self.canvases['rpm'].pack(side=tk.LEFT, padx=5)
        self.canvases['speed'] = tk.Canvas(gauge_frame, width=150, height=150, bg='black', highlightthickness=0)  # Reduced size
        self.canvases['speed'].pack(side=tk.LEFT, padx=5)
        odometer_frame = tk.Frame(top_frame, bg='#404040')
        odometer_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        tk.Label(odometer_frame, text="Odometer [km]", fg='white', bg='#404040', font=('Arial', 8)).pack()
        self.widgets['odometer_label'] = tk.Label(odometer_frame, text="0.000", fg='green', bg='black', font=('Arial', 12, 'bold'))
        self.widgets['odometer_label'].pack()

        # Middle panel: Position/Orientation, Controls
        middle_frame = tk.Frame(main_frame, bg='#2b2b2b')
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        pos_frame = tk.LabelFrame(middle_frame, text="Position/Orientation", fg='white', bg='#404040', font=('Arial', 10, 'bold'))
        pos_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.create_position_displays(pos_frame)
        self.create_control_section(pos_frame)

        # Right panel: Rates, Buttons, Debug
        right_frame = tk.Frame(middle_frame, bg='#404040')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        self.create_rate_displays(right_frame)
        self.create_control_buttons(right_frame)
        if self.warning_visible:
            self.create_warning_section(right_frame)
        if self.debug_mode:
            self.create_debug_panel(right_frame)

    def create_position_displays(self, parent: tk.Widget) -> None:
        """Create position and angle displays using pack manager."""
        positions = [
            ("POS X [m]", "pos_x_m"),
            ("POS Y [m]", "pos_y_m"),
            ("POS Z [m]", "pos_z_m")
        ]
        angles = [
            ("Angle Roll [deg]", "angle_roll_deg"),
            ("Angle Pitch [deg]", "angle_pitch_deg"),
            ("Angle Yaw [deg]", "angle_yaw_deg")
        ]
        for (pos_label, pos_attr), (ang_label, ang_attr) in zip(positions, angles):
            row_frame = tk.Frame(parent, bg='#404040')
            row_frame.pack(fill=tk.X, padx=5, pady=2)  # Using pack instead of grid
            pos_sub_frame = tk.Frame(row_frame, bg='black', relief=tk.RAISED, bd=1)
            pos_sub_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
            tk.Label(pos_sub_frame, text=pos_label, fg='white', bg='black', font=('Arial', 6)).pack()
            self.widgets[f'{pos_attr}_label'] = tk.Label(pos_sub_frame, text=f"{getattr(self.vehicle_data, pos_attr):.3f}", fg='green', bg='black', font=('Arial', 10, 'bold'))
            self.widgets[f'{pos_attr}_label'].pack()
            ang_sub_frame = tk.Frame(row_frame, bg='black', relief=tk.RAISED, bd=1)
            ang_sub_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
            tk.Label(ang_sub_frame, text=ang_label, fg='white', bg='black', font=('Arial', 6)).pack()
            self.widgets[f'{ang_attr}_label'] = tk.Label(ang_sub_frame, text=f"{getattr(self.vehicle_data, ang_attr):.3f}", fg='green', bg='black', font=('Arial', 10, 'bold'))
            self.widgets[f'{ang_attr}_label'].pack()

    def create_control_section(self, parent: tk.Widget) -> None:
        """Create control section with pedals, gear selector, and sliders."""
        control_frame = tk.Frame(parent, bg='#404040')
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Pedal controls
        clutch_frame = tk.Frame(control_frame, bg='#404040')
        clutch_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(clutch_frame, text="Clutch  Brake  Accel", fg='white', bg='#404040', font=('Arial', 8)).pack()
        button_frame = tk.Frame(clutch_frame, bg='#404040')
        button_frame.pack()
        self.widgets['clutch_display'] = tk.Label(button_frame, text=f"{self.vehicle_data.clutch_value:.1f}", fg='white', bg='black', font=('Arial', 10), width=4, relief=tk.RAISED)
        self.widgets['clutch_display'].pack(side=tk.LEFT, padx=1)
        self.widgets['break_display'] = tk.Label(button_frame, text=f"{self.vehicle_data.break_value:.1f}", fg='white', bg='black', font=('Arial', 10), width=4, relief=tk.RAISED)
        self.widgets['break_display'].pack(side=tk.LEFT, padx=1)
        self.widgets['accel_display'] = tk.Label(button_frame, text=f"{self.vehicle_data.accel_value:.1f}", fg='white', bg='black', font=('Arial', 10), width=4, relief=tk.RAISED)
        self.widgets['accel_display'].pack(side=tk.LEFT, padx=1)
        
        # Sliders
        ttk.Label(clutch_frame, text="Clutch", style='TLabel').pack(anchor=tk.W)
        self.widgets['clutch_scale'] = ttk.Scale(clutch_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=lambda v: self.control_handler.set_clutch_value(float(v)), length=150)  # Reduced length
        self.widgets['clutch_scale'].set(self.vehicle_data.clutch_value)
        self.widgets['clutch_scale'].pack(fill=tk.X, padx=5)
        ttk.Label(clutch_frame, text="Brake", style='TLabel').pack(anchor=tk.W)
        self.widgets['break_scale'] = ttk.Scale(clutch_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=lambda v: self.control_handler.set_break_value(float(v)), length=150)  # Reduced length
        self.widgets['break_scale'].set(self.vehicle_data.break_value)
        self.widgets['break_scale'].pack(fill=tk.X, padx=5)
        ttk.Label(clutch_frame, text="Accel", style='TLabel').pack(anchor=tk.W)
        self.widgets['accel_scale'] = ttk.Scale(clutch_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=lambda v: self.control_handler.set_accel_value(float(v)), length=150)  # Reduced length
        self.widgets['accel_scale'].set(self.vehicle_data.accel_value)
        self.widgets['accel_scale'].pack(fill=tk.X, padx=5)
        
        # Histograms
        self.create_histograms(clutch_frame)
        
        # Gear selector
        self.create_gear_selector(control_frame)
        
        # Steering
        steering_frame = tk.Frame(control_frame, bg='#404040')
        steering_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        tk.Label(steering_frame, text="Steering Wheel Angle", fg='white', bg='#404040', font=('Arial', 8)).pack()
        self.canvases['steering'] = tk.Canvas(steering_frame, width=300, height=20, bg='black', highlightthickness=1, highlightbackground='white')  # Reduced size
        self.canvases['steering'].pack()
        self.widgets['steering_scale'] = ttk.Scale(steering_frame, from_=-780, to=780, orient=tk.HORIZONTAL, command=lambda v: self.control_handler.set_steering_wheel_angle(float(v)), length=300)  # Reduced length
        self.widgets['steering_scale'].set(self.vehicle_data.steering_wheel_angle)
        self.widgets['steering_scale'].pack(fill=tk.X, padx=5)

    def create_histograms(self, parent: tk.Widget) -> None:
        """Create histogram displays for pedal values."""
        histogram_frame = tk.Frame(parent, bg='#404040')
        histogram_frame.pack(pady=2)
        for pedal in ['clutch', 'break', 'accel']:
            canvas = tk.Canvas(histogram_frame, width=30, height=60, bg='black', highlightthickness=1, highlightbackground='white')  # Reduced size
            canvas.pack(side=tk.LEFT, padx=1)
            self.canvases[f'{pedal}_hist'] = canvas

    def draw_histogram(self, canvas: tk.Canvas, value: float, max_val: float = 100) -> None:
        """Draw a histogram bar chart."""
        canvas.delete("all")
        fill_level = int((value / max_val) * 8)
        for i in range(8):
            y = 55 - i * 7  # Adjusted for smaller canvas
            color = 'green' if value < 70 else 'orange' if value < 90 else 'red' if i < fill_level else 'gray20'
            canvas.create_rectangle(5, y, 25, y+5, fill=color, outline='gray40' if i >= fill_level else color)

    def create_gear_selector(self, parent: tk.Widget) -> None:
        """Create gear selector display and buttons."""
        gear_selector_frame = tk.Frame(parent, bg='#404040')
        gear_selector_frame.pack(side=tk.RIGHT, padx=10)
        self.canvases['gear_selector'] = tk.Canvas(gear_selector_frame, width=50, height=60, bg='black', highlightthickness=1, highlightbackground='white')  # Adjusted size for fewer gears
        self.canvases['gear_selector'].pack()
        gear_buttons_frame = tk.Frame(gear_selector_frame, bg='#404040')
        gear_buttons_frame.pack(pady=2)
        gears = ['P', 'R', 'N', 'D', 'L']  # Removed 1-6
        self.gear_var = tk.StringVar(value=self.vehicle_data.gear)
        for i, gear in enumerate(gears):
            btn = tk.Button(gear_buttons_frame, text=gear, width=2, command=lambda g=gear: self.control_handler.set_gear(g), font=('Arial', 8))
            btn.grid(row=i // 2, column=i % 2, padx=1)
            self.widgets[f'gear_btn_{gear}'] = btn

    def draw_gear_selector(self, canvas: tk.Canvas, current_gear: str) -> None:
        """Draw gear selector display."""
        canvas.delete("all")
        gears = ['P', 'R', 'N', 'D', 'L']  # Removed 1-6
        for i, gear in enumerate(gears):
            y = 15 + i * 10  # Adjusted for smaller canvas
            color = 'green' if gear == current_gear else 'white'
            canvas.create_text(25, y, text=gear, fill=color, font=('Arial', 8, 'bold'))
            if gear == current_gear:
                canvas.create_rectangle(40, y-4, 48, y+4, fill='green', outline='green')

    def draw_gauge(self, canvas: tk.Canvas, title: str, min_val: float, max_val: float, current_val: float, cx: int, cy: int, radius: int) -> None:
        """Draw an analog gauge."""
        canvas.delete("all")
        color = 'green' if current_val < (max_val * 0.5) else 'orange' if current_val < (max_val * 0.75) else 'red'
        canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline=color, width=2)
        canvas.create_text(cx, cy+20, text=title, fill='white', font=('Arial', 8))
        for i in range(int(min_val), int(max_val)+1, max(1, int((max_val-min_val)/8))):
            angle = math.radians(225 - (i-min_val)/(max_val-min_val) * 270)
            x1, y1 = cx + (radius-10) * math.cos(angle), cy + (radius-10) * math.sin(angle)
            x2, y2 = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            canvas.create_line(x1, y1, x2, y2, fill='white', width=1)
            text_x, text_y = cx + (radius-15) * math.cos(angle), cy + (radius-15) * math.sin(angle)
            canvas.create_text(text_x, text_y, text=str(i), fill='white', font=('Arial', 6))
        needle_angle = math.radians(225 - (current_val-min_val)/(max_val-min_val) * 270)
        needle_x, needle_y = cx + (radius-10) * math.cos(needle_angle), cy + (radius-10) * math.sin(needle_angle)
        canvas.create_line(cx, cy, needle_x, needle_y, fill='red', width=3)
        canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill='red', outline='red')
        canvas.create_text(cx, cy-20, text=f"{current_val:.1f}", fill=color, font=('Arial', 10, 'bold'))

    def draw_steering_indicator(self, canvas: tk.Canvas, angle: float) -> None:
        """Draw steering angle indicator."""
        canvas.delete("all")
        canvas.create_line(50, 10, 250, 10, fill='white', width=2)  # Adjusted for smaller canvas
        for i in range(-780, 781, 260):
            x = 150 + i * (100/780)  # Adjusted scale
            if 50 <= x <= 250:
                canvas.create_line(x, 5, x, 15, fill='white', width=1)
                canvas.create_text(x, 18, text=str(i), fill='white', font=('Arial', 6))
        angle = max(-780, min(780, angle))
        current_pos = 150 + angle * (100/780)
        if 50 <= current_pos <= 250:
            canvas.create_polygon(current_pos-4, 2, current_pos+4, 2, current_pos, 10, fill='cyan', outline='cyan')

    def create_rate_displays(self, parent: tk.Widget) -> None:
        """Create rate displays."""
        rates = [
            ("Roll Rate [deg/s]", "roll_rate_degs"),
            ("Pitch Rate [deg/s]", "pitch_rate_degs"),
            ("Yaw Rate [deg/s]", "yaw_rate_degs")
        ]
        for label, attr in rates:
            frame = tk.Frame(parent, bg='black', relief=tk.RAISED, bd=1)
            frame.pack(fill=tk.X, pady=2)
            tk.Label(frame, text=label, fg='white', bg='black', font=('Arial', 6)).pack()
            self.widgets[f'{attr}_label'] = tk.Label(frame, text=f"{getattr(self.vehicle_data, attr):.2f}", fg='green', bg='black', font=('Arial', 10, 'bold'))
            self.widgets[f'{attr}_label'].pack()

    def create_control_buttons(self, parent: tk.Widget) -> None:
        """Create control buttons."""
        measure_frame = tk.LabelFrame(parent, text="Measurement", fg='white', bg='#404040', font=('Arial', 8, 'bold'))
        measure_frame.pack(fill=tk.X, pady=2)
        button_frame = tk.Frame(measure_frame, bg='#404040')
        button_frame.pack(pady=2)
        self.widgets['pause_button'] = tk.Button(button_frame, text="Pause", bg='orange', fg='black', font=('Arial', 8, 'bold'), width=6, command=self.toggle_pause)
        self.widgets['pause_button'].pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="STOP", bg='red', fg='white', font=('Arial', 8, 'bold'), width=6, command=self.stop_simulation).pack(side=tk.LEFT, padx=2)
        control_buttons_frame = tk.Frame(parent, bg='#404040')
        control_buttons_frame.pack(fill=tk.X, pady=5)
        self.widgets['power_button'] = tk.Button(control_buttons_frame, text="START Vehicle", bg='lightblue', fg='black', font=('Arial', 8), width=15, command=self.control_handler.toggle_vehicle_power)
        self.widgets['power_button'].pack(pady=1)
        tk.Button(control_buttons_frame, text="Reset Vehicle", bg='lightblue', fg='black', font=('Arial', 8), width=15, command=self.reset_vehicle).pack(pady=1)
        maneuver_frame = tk.Frame(control_buttons_frame, bg='#404040')
        maneuver_frame.pack(pady=2)
        tk.Label(maneuver_frame, text="Maneuvers", bg='#404040', fg='white', font=('Arial', 8, 'bold')).pack()
        self.maneuver_var = tk.StringVar(self.root)
        maneuver_names = list(self.control_handler.all_maneuver_presets.keys())
        if maneuver_names:
            self.maneuver_var.set(maneuver_names[0])
        self.widgets['maneuver_dropdown'] = ttk.Combobox(maneuver_frame, textvariable=self.maneuver_var, values=maneuver_names, state="readonly", width=15)
        self.widgets['maneuver_dropdown'].pack(pady=2)
        self.widgets['start_maneuver_btn'] = tk.Button(maneuver_frame, text="Start Maneuver", bg='lightblue', fg='black', font=('Arial', 8), width=15, command=lambda: self.start_maneuver())
        self.widgets['start_maneuver_btn'].pack(pady=1)
        self.widgets['stop_maneuver_btn'] = tk.Button(maneuver_frame, text="Stop Maneuver", bg='lightblue', fg='black', font=('Arial', 8), width=15, command=self.stop_maneuver)
        self.widgets['stop_maneuver_btn'].pack(pady=1)
        self.widgets['status_label'] = tk.Label(parent, text="READY", fg='white', bg='green', font=('Arial', 8), relief=tk.RAISED, bd=1)
        self.widgets['status_label'].pack(fill=tk.X, padx=5, pady=5)

    def create_warning_section(self, parent: tk.Widget) -> None:
        """Create warning section."""
        warning_frame = tk.Frame(parent, bg='yellow', relief=tk.RAISED, bd=2)
        warning_frame.pack(fill=tk.X, pady=2)
        tk.Label(warning_frame, text="System Alert", bg='yellow', fg='black', font=('Arial', 8, 'bold')).pack()
        tk.Label(warning_frame, text="Simulation Mode", bg='yellow', fg='black', font=('Arial', 6)).pack()
        tk.Button(warning_frame, text="×", bg='yellow', fg='red', font=('Arial', 10, 'bold'), width=2, command=self.close_warning).place(relx=1.0, rely=0.0, anchor='ne')

    def create_debug_panel(self, parent: tk.Widget) -> None:
        """Create debug panel."""
        debug_frame = tk.LabelFrame(parent, text="Debugging Logs", fg='white', bg='#404040', font=('Arial', 8, 'bold'))
        debug_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        self.log_text_widget = tk.Text(debug_frame, height=6, width=60, bg='#1e1e1e', fg='#00ff00', font=('Consolas', 8), state=tk.DISABLED)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scrollbar = ttk.Scrollbar(self.log_text_widget, command=self.log_text_widget.yview)
        self.log_text_widget.config(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, in_=debug_frame)
        self.log_handler = TextHandler(self.log_text_widget)
        if self.debug_mode:
            logging.getLogger().addHandler(self.log_handler)
            self.log_text_widget.config(state=tk.NORMAL)

    def update_gui(self) -> None:
        """Update all GUI elements with current data."""
        try:
            self.draw_gauge(self.canvases['rpm'], "RPM\nx 1000", 0, 8, self.vehicle_data.rpm/1000, 75, 75, 60)
            self.draw_gauge(self.canvases['speed'], "Km/h", 0, 300, self.vehicle_data.speed_kmh, 75, 75, 60)
            self.widgets['odometer_label'].config(text=f"{self.vehicle_data.odometer_km:.3f}")
            for attr in ['pos_x_m', 'pos_y_m', 'pos_z_m', 'angle_roll_deg', 'angle_pitch_deg', 'angle_yaw_deg']:
                if f'{attr}_label' in self.widgets:
                    self.widgets[f'{attr}_label'].config(text=f"{getattr(self.vehicle_data, attr):.3f}")
            for attr in ['roll_rate_degs', 'pitch_rate_degs', 'yaw_rate_degs']:
                if f'{attr}_label' in self.widgets:
                    self.widgets[f'{attr}_label'].config(text=f"{getattr(self.vehicle_data, attr):.2f}")
            if not self.vehicle_data.maneuver_active:
                self.widgets['clutch_scale'].set(self.vehicle_data.clutch_value)
                self.widgets['break_scale'].set(self.vehicle_data.break_value)
                self.widgets['accel_scale'].set(self.vehicle_data.accel_value)
                self.widgets['steering_scale'].set(self.vehicle_data.steering_wheel_angle)
            self.widgets['clutch_display'].config(text=f"{self.vehicle_data.clutch_value:.1f}")
            self.widgets['break_display'].config(text=f"{self.vehicle_data.break_value:.1f}")
            self.widgets['accel_display'].config(text=f"{self.vehicle_data.accel_value:.1f}")
            for pedal in ['clutch', 'break', 'accel']:
                if f'{pedal}_hist' in self.canvases:
                    self.draw_histogram(self.canvases[f'{pedal}_hist'], getattr(self.vehicle_data, f'{pedal}_value'))
            self.draw_gear_selector(self.canvases['gear_selector'], self.vehicle_data.gear)
            self.draw_steering_indicator(self.canvases['steering'], self.vehicle_data.steering_wheel_angle)
            if self.vehicle_data.vehicle_started:
                self.widgets['power_button'].config(text="STOP Vehicle")
            else:
                self.widgets['power_button'].config(text="START Vehicle")
            if self.control_handler.is_paused:
                self.widgets['status_label'].config(text="PAUSED", bg='orange')
                self.widgets['pause_button'].config(text="Resume")
            else:
                self.widgets['status_label'].config(text="RUNNING" if self.control_handler.is_running else "STOPPED", bg='green' if self.control_handler.is_running else 'red')
                self.widgets['pause_button'].config(text="Pause")
            control_state = tk.DISABLED if self.vehicle_data.maneuver_active else tk.NORMAL
            for widget_name in ['clutch_scale', 'break_scale', 'accel_scale', 'steering_scale']:
                if widget_name in self.widgets:
                    self.widgets[widget_name].config(state=control_state)
            for gear in ['P', 'R', 'N', 'D', 'L']:  # Updated to match new gear list
                if f'gear_btn_{gear}' in self.widgets:
                    self.widgets[f'gear_btn_{gear}'].config(state=control_state)
            if self.vehicle_data.maneuver_active:
                self.widgets['maneuver_dropdown'].config(state=tk.DISABLED)
                self.widgets['start_maneuver_btn'].config(state=tk.DISABLED)
                self.widgets['stop_maneuver_btn'].config(state=tk.NORMAL)
            else:
                self.widgets['maneuver_dropdown'].config(state="readonly")
                self.widgets['start_maneuver_btn'].config(state=tk.NORMAL)
                self.widgets['stop_maneuver_btn'].config(state=tk.DISABLED)
            if self.debug_mode and self.log_text_widget:
                self.log_text_widget.config(state=tk.NORMAL)
                self.log_text_widget.insert(tk.END, f"Timestamp: {datetime.now().strftime('%H:%M:%S')} - Data Valid: {self.vehicle_data.validate()}\n")
                self.log_text_widget.see(tk.END)
                self.log_text_widget.config(state=tk.DISABLED)
        except Exception as e:
            logger.error(f"Error updating GUI: {e}")

    def start_sim_thread(self) -> None:
        """Start the simulation thread."""
        if not self.sim_thread_running:
            self.sim_thread_running = True
            self.sim_thread = threading.Thread(target=self._run_simulation, daemon=True)
            self.sim_thread.start()
            logger.info("Simulation thread started.")

    def _run_simulation(self) -> None:
        """Worker function for the simulation thread."""
        while self.sim_thread_running:
            self.control_handler.simulate_vehicle_data()
            time.sleep(self.config.get("refresh_rate", 1000) / 1000.0)

    def stop_sim_thread(self) -> None:
        """Stop the simulation thread."""
        if self.sim_thread_running:
            self.sim_thread_running = False
            logger.info("Simulation thread stopped.")

    def update_gui_periodic(self) -> None:
        """Periodically update the GUI."""
        if self.root.winfo_exists():
            self.update_gui()
            self.root.after(self.config.get("refresh_rate", 100), self.update_gui_periodic)

    def start_maneuver(self) -> None:
        """Start vehicle maneuver."""
        if self.vehicle_data.vehicle_started:
            self.control_handler.start_maneuver(self.maneuver_var.get())
            messagebox.showinfo("Maneuver", f"Maneuver {self.maneuver_var.get()} started")
        else:
            messagebox.showwarning("Maneuver", "Cannot start maneuver: Vehicle is off")

    def stop_maneuver(self) -> None:
        """Stop vehicle maneuver."""
        self.control_handler.stop_maneuver()
        messagebox.showinfo("Maneuver", "Maneuver stopped")

    def reset_vehicle(self) -> None:
        """Reset vehicle to default state."""
        if messagebox.askyesno("Reset", "Are you sure you want to reset the vehicle?"):
            self.control_handler.reset_vehicle(self.config_manager.default_config.get("vehicle_data", {}))
            messagebox.showinfo("Reset", "Vehicle has been reset")

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        self.control_handler.toggle_pause()

    def stop_simulation(self) -> None:
        """Stop the simulation."""
        self.control_handler.stop_simulation()

    def close_warning(self) -> None:
        """Close warning panel."""
        self.warning_visible = False
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame) and widget.pack_info().get('side') == 'right':
                widget.destroy()
                break
        self.create_gui()  # Recreate GUI without warning

    def toggle_debug_mode(self) -> None:
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        self.config['debug_mode'] = self.debug_mode
        if self.debug_mode:
            self.create_debug_panel(self.root.winfo_children()[-1])
        else:
            for handler in logging.getLogger().handlers:
                if isinstance(handler, TextHandler):
                    logging.getLogger().removeHandler(handler)
            if self.log_text_widget:
                self.log_text_widget.destroy()
                self.log_text_widget = None
        logger.info(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}.")

    def toggle_simulation(self) -> None:
        """Toggle simulation mode."""
        self.control_handler.simulation_enabled = not self.control_handler.simulation_enabled
        logger.info(f"Simulation {'enabled' if self.control_handler.simulation_enabled else 'disabled'}")

    def load_config_dialog(self) -> None:
        """Load configuration from file."""
        filename = filedialog.askopenfilename(title="Select Configuration File", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filename:
            try:
                new_config = self.config_manager.load_config(filename)
                self.config.update(new_config)
                self.vehicle_data = VehicleData(**new_config.get("vehicle_data", {}))
                self.control_handler.vehicle_data = self.vehicle_data
                self.debug_mode = new_config.get("debug_mode", False)
                if self.debug_mode:
                    self.create_debug_panel(self.root.winfo_children()[-1])
                else:
                    for handler in logging.getLogger().handlers:
                        if isinstance(handler, TextHandler):
                            logging.getLogger().removeHandler(handler)
                    if self.log_text_widget:
                        self.log_text_widget.destroy()
                        self.log_text_widget = None
                messagebox.showinfo("Success", f"Configuration loaded from {filename}")
                logger.info(f"Configuration loaded from {filename}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                messagebox.showerror("Error", f"Failed to load configuration: {e}")

    def save_config_dialog(self) -> None:
        """Save current configuration to file."""
        filename = filedialog.asksaveasfilename(title="Save Configuration As", defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filename:
            try:
                self.config['vehicle_data'] = {
                    'rpm': self.vehicle_data.rpm,
                    'speed_kmh': self.vehicle_data.speed_kmh,
                    'odometer_km': self.vehicle_data.odometer_km,
                    'gear': self.vehicle_data.gear,
                    'pos_x_m': self.vehicle_data.pos_x_m,
                    'pos_y_m': self.vehicle_data.pos_y_m,
                    'pos_z_m': self.vehicle_data.pos_z_m,
                    'angle_roll_deg': self.vehicle_data.angle_roll_deg,
                    'angle_pitch_deg': self.vehicle_data.angle_pitch_deg,
                    'angle_yaw_deg': self.vehicle_data.angle_yaw_deg,
                    'roll_rate_degs': self.vehicle_data.roll_rate_degs,
                    'pitch_rate_degs': self.vehicle_data.pitch_rate_degs,
                    'yaw_rate_degs': self.vehicle_data.yaw_rate_degs,
                    'clutch_value': self.vehicle_data.clutch_value,
                    'break_value': self.vehicle_data.break_value,
                    'accel_value': self.vehicle_data.accel_value,
                    'steering_wheel_angle': self.vehicle_data.steering_wheel_angle,
                    'vehicle_started': self.vehicle_data.vehicle_started,
                    'maneuver_active': self.vehicle_data.maneuver_active
                }
                self.config_manager.save_config(self.config, filename)
                messagebox.showinfo("Success", f"Configuration saved to {filename}")
                logger.info(f"Configuration saved to {filename}")
            except Exception as e:
                logger.error(f"Error saving configuration: {e}")
                messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def show_about(self) -> None:
        """Show about dialog."""
        about_text = """
Vehicle Control Panel Simulation v1.1

Features:
• Real-time vehicle telemetry display
• Interactive gauges, sliders, and controls
• Configuration management (Load/Save)
• Maneuver execution system
• Debug mode with real-time logging
• Enhanced simulation with vehicle power state
• Non-hanging GUI using threading

Developed with Python and Tkinter
"""
        messagebox.showinfo("About", about_text)

    def on_closing(self) -> None:
        """Handle application closing."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            logger.info("Application closing initiated by user.")
            self.stop_sim_thread()
            try:
                self.config['vehicle_data'] = {
                    'rpm': self.vehicle_data.rpm,
                    'speed_kmh': self.vehicle_data.speed_kmh,
                    'odometer_km': self.vehicle_data.odometer_km,
                    'gear': self.vehicle_data.gear,
                    'pos_x_m': self.vehicle_data.pos_x_m,
                    'pos_y_m': self.vehicle_data.pos_y_m,
                    'pos_z_m': self.vehicle_data.pos_z_m,
                    'angle_roll_deg': self.vehicle_data.angle_roll_deg,
                    'angle_pitch_deg': self.vehicle_data.angle_pitch_deg,
                    'angle_yaw_deg': self.vehicle_data.angle_yaw_deg,
                    'roll_rate_degs': self.vehicle_data.roll_rate_degs,
                    'pitch_rate_degs': self.vehicle_data.pitch_rate_degs,
                    'yaw_rate_degs': self.vehicle_data.yaw_rate_degs,
                    'clutch_value': self.vehicle_data.clutch_value,
                    'break_value': self.vehicle_data.break_value,
                    'accel_value': self.vehicle_data.accel_value,
                    'steering_wheel_angle': self.vehicle_data.steering_wheel_angle,
                    'vehicle_started': self.vehicle_data.vehicle_started,
                    'maneuver_active': self.vehicle_data.maneuver_active
                }
                self.config['debug_mode'] = self.debug_mode
                self.config['simulation_enabled'] = self.control_handler.simulation_enabled
                self.config_manager.save_config(self.config)
                logger.info("Configuration saved on exit.")
            except Exception as e:
                logger.error(f"Error saving configuration on exit: {e}")
            for handler in logging.getLogger().handlers:
                if isinstance(handler, TextHandler):
                    logging.getLogger().removeHandler(handler)
            self.root.destroy()
            logger.info("Application closed.")

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    app = VehicleControlPanel(root)
    root.mainloop()