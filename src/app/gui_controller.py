"""
GUI Controller — Module 19 per Architecture v1.2 §4.

Provides the standalone desktop interface for the evaluator demonstration.
Allows configuration of scenarios, switching between Simulation and MP4 modes,
and viewing the live Tracking visualization.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk

from src.app.app_controller import AppController
from src.evaluation.benchmark_manager import BenchmarkManager
from src.app.visualization_engine import VisualizationEngine
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import FrameSource


class GUIController:
    """
    Main Tkinter application for the FSOC Virtual Camera Tracker.
    """

    def __init__(self, root: tk.Tk, app: AppController) -> None:
        self.root = root
        self.app = app
        self.root.title("SIH 2026 - FSOC Virtual Camera Tracker")
        self.root.geometry("1024x768")

        self.viz_engine = VisualizationEngine()
        self.benchmark_manager = BenchmarkManager(self.app)
        self.is_running = False
        self.thread: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        # Main Layout
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar - Controls
        self.sidebar = ttk.Frame(self.main_pane, width=300, relief=tk.SUNKEN)
        self.main_pane.add(self.sidebar, weight=0)

        # Right Viewport - Video
        self.viewport = ttk.Frame(self.main_pane, relief=tk.SUNKEN)
        self.main_pane.add(self.viewport, weight=1)

        self._build_sidebar()
        self._build_viewport()

    def _build_sidebar(self) -> None:
        # Mode Selection
        mode_frame = ttk.LabelFrame(self.sidebar, text="Operation Mode")
        mode_frame.pack(fill=tk.X, padx=5, pady=5)

        self.mode_var = tk.StringVar(value="SIMULATION")
        ttk.Radiobutton(mode_frame, text="Simulation (Benchmark 1)", variable=self.mode_var, value="SIMULATION", command=self._on_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="MP4 Video (Benchmark 2)", variable=self.mode_var, value="MP4", command=self._on_mode_change).pack(anchor=tk.W)

        # MP4 File picker
        self.mp4_frame = ttk.Frame(mode_frame)
        self.mp4_path_var = tk.StringVar(value="")
        ttk.Label(self.mp4_frame, text="MP4 File:").pack(side=tk.LEFT)
        ttk.Entry(self.mp4_frame, textvariable=self.mp4_path_var, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.mp4_frame, text="Browse", command=self._browse_mp4).pack(side=tk.LEFT)
        # Will be packed dynamically via _on_mode_change

        # Configuration (Simulation only)
        self.config_frame = ttk.LabelFrame(self.sidebar, text="Simulation Configuration")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)

        # Motion Type
        ttk.Label(self.config_frame, text="Target Motion:").grid(row=0, column=0, sticky=tk.W)
        self.motion_var = tk.StringVar(value="STRAIGHT_LINE")
        ttk.Combobox(self.config_frame, textvariable=self.motion_var, values=["STRAIGHT_LINE", "CIRCULAR", "FIGURE_8", "RANDOM"]).grid(row=0, column=1)

        # Atmospheric
        ttk.Label(self.config_frame, text="Atmospheric:").grid(row=1, column=0, sticky=tk.W)
        self.atmos_var = tk.StringVar(value="CLEAR")
        ttk.Combobox(self.config_frame, textvariable=self.atmos_var, values=["CLEAR", "HAZE", "FOG", "RAIN", "LOW_LIGHT"]).grid(row=1, column=1)

        # Playback Controls
        ctrl_frame = ttk.LabelFrame(self.sidebar, text="Playback")
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        self.btn_start = ttk.Button(ctrl_frame, text="Start Tracker", command=self._start)
        self.btn_start.pack(fill=tk.X, pady=2)
        
        self.btn_stop = ttk.Button(ctrl_frame, text="Stop Tracker", command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X, pady=2)

        self._on_mode_change()

    def _build_viewport(self) -> None:
        self.canvas = tk.Canvas(self.viewport, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW)

    def _on_mode_change(self) -> None:
        mode = self.mode_var.get()
        if mode == "MP4":
            self.mp4_frame.pack(fill=tk.X, pady=5)
            # Disable sim configs
            for child in self.config_frame.winfo_children():
                child.configure(state=tk.DISABLED)
        else:
            self.mp4_frame.pack_forget()
            # Enable sim configs
            for child in self.config_frame.winfo_children():
                child.configure(state=tk.NORMAL)

    def _browse_mp4(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select MP4 Video",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
        )
        if filename:
            self.mp4_path_var.set(filename)

    def _update_config(self) -> None:
        """Update system config based on UI inputs."""
        cfg = self.app.config_manager.config
        mode = self.mode_var.get()
        cfg.simulation.mode = mode

        if mode == "MP4":
            path = self.mp4_path_var.get()
            if not path:
                raise ValueError("MP4 path not specified.")
            cfg.simulation.mp4_path = path
        else:
            cfg.motion.pattern = self.motion_var.get()
            cfg.atmospheric.condition = self.atmos_var.get()

    def _start(self) -> None:
        try:
            self._update_config()
            self.app.initialize()
            
            # Reset components
            if self.app.tracking_engine:
                self.app.tracking_engine.reset()
            if self.app.tracking_state_manager:
                self.app.tracking_state_manager.reset()
            if self.app.ptz_controller:
                self.app.ptz_controller.reset()

            self.is_running = True
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.NORMAL)

            # Start worker thread
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

        except Exception as e:
            messagebox.showerror("Initialization Error", str(e))

    def _stop(self) -> None:
        self.is_running = False
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)

    def _run_loop(self) -> None:
        try:
            while self.is_running:
                packet = self.app.get_next_frame()
                if packet is None:
                    break

                t_start = time.perf_counter()

                # Tracking Pipeline
                roi = self.app.tracking_engine.get_roi(packet.width, packet.height) if self.app.tracking_engine else None
                detection_res = self.app.detection_engine.detect(packet, roi=roi)
                ident_res = self.app.candidate_identifier.identify(detection_res.candidates)
                
                centroid_res = None
                if ident_res.valid and ident_res.selected_candidate is not None:
                    centroid_res = self.app.centroid_estimator.estimate(packet, ident_res.selected_candidate)
                
                track_res = self.app.tracking_engine.update(centroid_res, frame_number=packet.frame_number, timestamp=packet.timestamp)
                state_res = self.app.tracking_state_manager.update(track_res)

                # Control
                ptz_cmd = None
                if self.app.ptz_controller and packet.source == FrameSource.SIMULATION:
                    dt = 1.0 / self.app.config_manager.config.camera.update_rate_hz
                    ptz_cmd = self.app.ptz_controller.compute(track_res, state_res, packet.width, packet.height, dt)
                    if self.app.camera_model and ptz_cmd.valid:
                        self.app.camera_model.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)

                t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

                from src.frame.data_contracts import TrackerOutput
                tracker_output = TrackerOutput(
                    frame_number=packet.frame_number,
                    timestamp=packet.timestamp,
                    state=state_res.state,
                    previous_state=state_res.previous_state,
                    transition_reason=state_res.transition_reason,
                    centroid=centroid_res,
                    track=track_res,
                    detection_valid=ident_res.valid,
                    candidate_count=len(detection_res.candidates),
                    confidence=state_res.confidence_level,
                    roi=roi,
                    processing_time_ms=t_elapsed_ms
                )

                ground_truth = None
                if self.app.ground_truth_provider:
                    ground_truth = self.app.ground_truth_provider.get_truth(packet.frame_number)
                
                if self.app._metrics_engine:
                    self.app._metrics_engine.update(
                        tracker_output,
                        ground_truth,
                        camera_width=packet.width,
                        camera_height=packet.height
                    )

                # Rendering
                display_img = self.viz_engine.render(packet, tracker_output, ground_truth, draw_ground_truth=True)
                
                # Update UI
                self._update_canvas(display_img)
                
                # Sleep to maintain approx FPS
                time.sleep(max(0, (1.0/30.0) - (time.perf_counter() - t_start)))
                
        except Exception as e:
            print(f"Error in tracking loop: {e}")
        finally:
            # Safe call back to main thread
            self.root.after(0, self._stop)

    def _update_canvas(self, bgr_img: np.ndarray) -> None:
        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_img)
        # Center in canvas
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        # Scale preserving aspect ratio
        iw, ih = img.size
        if iw > 0 and ih > 0 and cw > 0 and ch > 0:
            ratio = min(cw/iw, ch/ih)
            new_w, new_h = int(iw*ratio), int(ih*ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        
        photo = ImageTk.PhotoImage(image=img)
        # We must keep a reference so it doesn't get garbage collected
        self.canvas.image = photo
        
        # Center coordinates
        x = (cw - new_w) // 2 if cw > new_w else 0
        y = (ch - new_h) // 2 if ch > new_h else 0
        
        self.canvas.itemconfig(self.image_id, image=photo)
        self.canvas.coords(self.image_id, x, y)


def launch_gui(app: AppController) -> None:
    root = tk.Tk()
    gui = GUIController(root, app)
    root.mainloop()
