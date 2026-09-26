from __future__ import annotations
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout, QSpinBox, 
    QDoubleSpinBox, QComboBox, QCheckBox, QPushButton, QLabel, QGroupBox,
    QSlider, QGridLayout, QFrame, QLineEdit
)
from PySide6.QtCore import Signal, Qt
from src.app.app_controller import AppController
from src.frame.data_contracts import MotionType, AtmosphericCondition, NoiseType, PlatformMotionType
from src.config.config_manager import BeaconConfig


class ConfigPanel(QWidget):
    config_changed = Signal()

    def __init__(self, app_controller: AppController):
        super().__init__()
        self.app = app_controller
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.secondary_beacons: List[Dict[str, Any]] = []
        
        # Camera Tab
        self.cam_tab = QWidget()
        cam_layout = QFormLayout(self.cam_tab)
        self.cam_w = QSpinBox(); self.cam_w.setRange(100, 4000); self.cam_w.setValue(640)
        self.cam_h = QSpinBox(); self.cam_h.setRange(100, 4000); self.cam_h.setValue(480)
        self.cam_fov = QDoubleSpinBox(); self.cam_fov.setRange(1.0, 100.0); self.cam_fov.setValue(4.0)
        self.cam_fps = QSpinBox(); self.cam_fps.setRange(10, 120); self.cam_fps.setValue(30)
        cam_layout.addRow("Width", self.cam_w)
        cam_layout.addRow("Height", self.cam_h)
        cam_layout.addRow("FOV (deg)", self.cam_fov)
        cam_layout.addRow("Base FPS", self.cam_fps)
        self.tabs.addTab(self.cam_tab, "Camera")
        
        # Target / Beacons Tab
        self.tgt_tab = QWidget()
        tgt_outer_layout = QVBoxLayout(self.tgt_tab)
        
        primary_group = QGroupBox("Primary Beacon")
        tgt_layout = QFormLayout(primary_group)
        self.tgt_size = QSpinBox(); self.tgt_size.setRange(2, 50); self.tgt_size.setValue(10)
        self.tgt_intensity = QSpinBox(); self.tgt_intensity.setRange(10, 255); self.tgt_intensity.setValue(220)
        
        # Dual Speed Control (SpinBox + Slider + Quick Presets)
        self.tgt_speed = QDoubleSpinBox()
        self.tgt_speed.setRange(0.0, 500.0)
        self.tgt_speed.setValue(50.0)
        self.tgt_speed.setSingleStep(5.0)
        self.tgt_speed.setSuffix(" px/s")

        self.tgt_speed_slider = QSlider(Qt.Horizontal)
        self.tgt_speed_slider.setRange(0, 500)
        self.tgt_speed_slider.setValue(50)
        self.tgt_speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        self.tgt_speed.valueChanged.connect(self._on_speed_spinbox_changed)

        # Quick preset buttons row
        preset_layout = QHBoxLayout()
        preset_layout.setContentsMargins(0, 2, 0, 2)
        preset_layout.addWidget(QLabel("Presets:"))
        for label, val in [("30", 30.0), ("80", 80.0), ("150", 150.0), ("300", 300.0), ("500", 500.0)]:
            p_btn = QPushButton(label)
            p_btn.setToolTip(f"Set speed to {val} px/s")
            p_btn.setStyleSheet("padding: 2px 6px; font-size: 10px; min-height: 20px;")
            p_btn.clicked.connect(lambda _, v=val: self.tgt_speed.setValue(v))
            preset_layout.addWidget(p_btn)
        preset_layout.addStretch()

        self.tgt_motion = QComboBox()
        self.tgt_motion.addItems([e.value for e in MotionType])
        
        tgt_layout.addRow("Size (px)", self.tgt_size)
        tgt_layout.addRow("Intensity (0-255)", self.tgt_intensity)
        tgt_layout.addRow("Speed", self.tgt_speed)
        tgt_layout.addRow("Speed Slider", self.tgt_speed_slider)
        tgt_layout.addRow("", preset_layout)
        tgt_layout.addRow("Motion Type", self.tgt_motion)
        tgt_outer_layout.addWidget(primary_group)
        
        # Secondary Beacons Section (P1 Multi-Beacon)
        self.sec_group = QGroupBox("Synthetic Distractor Beacons (Max 3)")
        self.sec_layout = QVBoxLayout(self.sec_group)
        self.sec_beacons_container = QVBoxLayout()
        self.sec_layout.addLayout(self.sec_beacons_container)
        
        self.btn_add_beacon = QPushButton("+ Add Secondary Beacon")
        self.btn_add_beacon.clicked.connect(self._add_secondary_beacon)
        self.sec_layout.addWidget(self.btn_add_beacon)
        
        self.lbl_beacon_status = QLabel("Secondary intensity must be < primary intensity")
        self.lbl_beacon_status.setStyleSheet("color: #777; font-size: 10px;")
        self.sec_layout.addWidget(self.lbl_beacon_status)
        
        tgt_outer_layout.addWidget(self.sec_group)
        tgt_outer_layout.addStretch()
        self.tabs.addTab(self.tgt_tab, "Target")
        
        # Disturbances Tab
        self.dist_tab = QWidget()
        dist_layout = QFormLayout(self.dist_tab)
        
        self.dist_atmos = QComboBox()
        self.dist_atmos.addItems([e.value for e in AtmosphericCondition])
        
        self.dist_noise = QComboBox()
        self.dist_noise.addItem("NONE")
        self.dist_noise.addItems([e.value for e in NoiseType])
        
        # Per-Noise Intensity Controls (P1)
        self.dist_gaussian_sigma = QDoubleSpinBox()
        self.dist_gaussian_sigma.setRange(0.0, 100.0)
        self.dist_gaussian_sigma.setValue(5.0)
        
        self.dist_sp_density = QDoubleSpinBox()
        self.dist_sp_density.setRange(0.0, 0.5)
        self.dist_sp_density.setDecimals(4)
        self.dist_sp_density.setSingleStep(0.005)
        self.dist_sp_density.setValue(0.01)
        
        self.dist_poisson_scale = QDoubleSpinBox()
        self.dist_poisson_scale.setRange(0.1, 10.0)
        self.dist_poisson_scale.setDecimals(2)
        self.dist_poisson_scale.setSingleStep(0.1)
        self.dist_poisson_scale.setValue(1.0)
        
        # Local Contrast Clutter Controls (P1 Stage 4.5)
        self.dist_local_contrast_enable = QCheckBox("Enable Local Contrast Clutter")
        self.dist_local_contrast_amp = QDoubleSpinBox()
        self.dist_local_contrast_amp.setRange(0.0, 120.0)
        self.dist_local_contrast_amp.setValue(40.0)
        
        self.dist_local_contrast_scale = QDoubleSpinBox()
        self.dist_local_contrast_scale.setRange(10.0, 300.0)
        self.dist_local_contrast_scale.setValue(80.0)
        
        self.dist_local_contrast_blobs = QSpinBox()
        self.dist_local_contrast_blobs.setRange(1, 20)
        self.dist_local_contrast_blobs.setValue(5)
        
        self.dist_platform = QComboBox()
        self.dist_platform.addItems([e.value for e in PlatformMotionType])
        
        self.dist_platform_amp = QDoubleSpinBox(); self.dist_platform_amp.setRange(0.0, 50.0); self.dist_platform_amp.setValue(1.0)
        self.dist_jitter_enable = QCheckBox("Enable Camera Jitter")
        self.dist_jitter_amp = QDoubleSpinBox(); self.dist_jitter_amp.setRange(0.0, 20.0); self.dist_jitter_amp.setValue(2.0)
        
        dist_layout.addRow("Atmosphere", self.dist_atmos)
        dist_layout.addRow("Noise Type", self.dist_noise)
        dist_layout.addRow("  Gaussian Sigma (px)", self.dist_gaussian_sigma)
        dist_layout.addRow("  S&P Density", self.dist_sp_density)
        dist_layout.addRow("  Poisson Scale", self.dist_poisson_scale)
        dist_layout.addRow("Local Contrast", self.dist_local_contrast_enable)
        dist_layout.addRow("  Clutter Amp", self.dist_local_contrast_amp)
        dist_layout.addRow("  Clutter Scale (px)", self.dist_local_contrast_scale)
        dist_layout.addRow("  Clutter Blobs", self.dist_local_contrast_blobs)
        dist_layout.addRow("Platform Motion", self.dist_platform)
        dist_layout.addRow("Platform Amp (px/f)", self.dist_platform_amp)
        dist_layout.addRow("Jitter Enabled", self.dist_jitter_enable)
        dist_layout.addRow("Jitter Amp (px/f)", self.dist_jitter_amp)
        self.tabs.addTab(self.dist_tab, "Disturbances")

        # Optional learned candidate classifier; disabled until explicitly enabled.
        self.aiml_tab = QWidget()
        aiml_layout = QFormLayout(self.aiml_tab)
        self.aiml_classifier_enable = QCheckBox("Use learned candidate classifier")
        self.aiml_model_dir = QLineEdit("models/candidate_classifier/v001")
        self.aiml_temporal_enable = QCheckBox("Use temporal residual predictor for candidate ranking")
        self.aiml_temporal_model_dir = QLineEdit("models/temporal_predictor/v001")
        self.aiml_model_dir.setToolTip(
            "Project-relative or absolute directory containing the versioned model package."
        )
        self.aiml_temporal_model_dir.setToolTip(
            "Project-relative or absolute directory containing the trained temporal model package."
        )
        aiml_layout.addRow("Candidate classifier", self.aiml_classifier_enable)
        aiml_layout.addRow("Model package", self.aiml_model_dir)
        aiml_layout.addRow("Temporal predictor", self.aiml_temporal_enable)
        aiml_layout.addRow("Temporal model", self.aiml_temporal_model_dir)
        self.tabs.addTab(self.aiml_tab, "AI/ML")
        
        self.layout.addWidget(self.tabs)
        
        self._connect_signals()

    def _on_speed_slider_changed(self, val: int):
        if abs(self.tgt_speed.value() - val) > 0.5:
            self.tgt_speed.blockSignals(True)
            self.tgt_speed.setValue(float(val))
            self.tgt_speed.blockSignals(False)
            self._on_change()

    def _on_speed_spinbox_changed(self, val: float):
        if self.tgt_speed_slider.value() != int(round(val)):
            self.tgt_speed_slider.blockSignals(True)
            self.tgt_speed_slider.setValue(int(round(val)))
            self.tgt_speed_slider.blockSignals(False)
        self._on_change()

    def _add_secondary_beacon(self):
        if len(self.secondary_beacons) >= 3:
            return
        
        idx = len(self.secondary_beacons) + 1
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(4)
        
        # Header
        hdr = QHBoxLayout()
        lbl = QLabel(f"Distractor Beacon #{idx}")
        lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #569cd6;")
        btn_del = QPushButton("Remove")
        btn_del.setFixedWidth(55)
        btn_del.setStyleSheet("background-color: #a33; color: white; padding: 2px 4px; font-size: 10px; min-height: 18px; border-radius: 2px;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(btn_del)
        card_layout.addLayout(hdr)
        
        # Grid parameters
        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 2)
        grid.setSpacing(4)

        max_int = max(10, self.tgt_intensity.value() - 10)
        spin_int = QSpinBox()
        spin_int.setRange(10, 255)
        spin_int.setValue(min(150, max_int))
        spin_int.setToolTip("Secondary Beacon Intensity (must be < primary)")
        
        spin_size = QSpinBox()
        spin_size.setRange(2, 50)
        spin_size.setValue(8)
        spin_size.setToolTip("Secondary Beacon Size (px)")
        
        spin_speed = QDoubleSpinBox()
        spin_speed.setRange(0.0, 500.0)
        spin_speed.setValue(40.0)
        spin_speed.setSingleStep(5.0)
        spin_speed.setSuffix(" px/s")
        spin_speed.setToolTip("Secondary Beacon Speed")
        
        grid.addWidget(QLabel("Intensity:"), 0, 0)
        grid.addWidget(spin_int, 0, 1)
        grid.addWidget(QLabel("Size:"), 0, 2)
        grid.addWidget(spin_size, 0, 3)
        grid.addWidget(QLabel("Speed:"), 1, 0)
        grid.addWidget(spin_speed, 1, 1, 1, 3)
        
        card_layout.addLayout(grid)
        
        row_data = {
            "widget": card,
            "intensity": spin_int,
            "size": spin_size,
            "speed": spin_speed,
        }
        
        btn_del.clicked.connect(lambda: self._remove_secondary_beacon(row_data))
        spin_int.valueChanged.connect(self._on_change)
        spin_size.valueChanged.connect(self._on_change)
        spin_speed.valueChanged.connect(self._on_change)
        
        self.secondary_beacons.append(row_data)
        self.sec_beacons_container.addWidget(card)
        
        if len(self.secondary_beacons) >= 3:
            self.btn_add_beacon.setEnabled(False)
            
        self._on_change()

    def _remove_secondary_beacon(self, row_data: Dict[str, Any]):
        if row_data in self.secondary_beacons:
            self.secondary_beacons.remove(row_data)
            self.sec_beacons_container.removeWidget(row_data["widget"])
            row_data["widget"].deleteLater()
            self.btn_add_beacon.setEnabled(True)
            self._on_change()
        
    def _connect_signals(self):
        # Emit signal on any value change
        self.cam_w.valueChanged.connect(self._on_change)
        self.cam_h.valueChanged.connect(self._on_change)
        self.cam_fov.valueChanged.connect(self._on_change)
        self.cam_fps.valueChanged.connect(self._on_change)
        
        self.tgt_size.valueChanged.connect(self._on_change)
        self.tgt_intensity.valueChanged.connect(self._on_change)
        self.tgt_motion.currentTextChanged.connect(self._on_change)
        
        self.dist_atmos.currentTextChanged.connect(self._on_change)
        self.dist_noise.currentTextChanged.connect(self._on_change)
        self.dist_gaussian_sigma.valueChanged.connect(self._on_change)
        self.dist_sp_density.valueChanged.connect(self._on_change)
        self.dist_poisson_scale.valueChanged.connect(self._on_change)
        
        self.dist_local_contrast_enable.toggled.connect(self._on_change)
        self.dist_local_contrast_amp.valueChanged.connect(self._on_change)
        self.dist_local_contrast_scale.valueChanged.connect(self._on_change)
        self.dist_local_contrast_blobs.valueChanged.connect(self._on_change)
        
        self.dist_platform.currentTextChanged.connect(self._on_change)
        self.dist_platform_amp.valueChanged.connect(self._on_change)
        
        self.dist_jitter_enable.toggled.connect(self._on_change)
        self.dist_jitter_amp.valueChanged.connect(self._on_change)
        self.aiml_classifier_enable.toggled.connect(self._on_change)
        self.aiml_model_dir.textChanged.connect(self._on_change)
        self.aiml_temporal_enable.toggled.connect(self._on_change)
        self.aiml_temporal_model_dir.textChanged.connect(self._on_change)

    def _on_change(self, *args, **kwargs):
        if hasattr(self.app, "set_target_speed"):
            self.app.set_target_speed(self.tgt_speed.value())
        if hasattr(self.app, "set_secondary_beacon_speed"):
            for idx, row in enumerate(self.secondary_beacons):
                self.app.set_secondary_beacon_speed(idx, row["speed"].value())
        self.config_changed.emit()

    def set_locked(self, locked: bool):
        """Lock configuration panel during benchmarks."""
        self.tabs.setEnabled(not locked)
        
    def apply_to_config(self, cfg):
        cfg.aiml.candidate_classifier_enabled = self.aiml_classifier_enable.isChecked()
        cfg.aiml.candidate_model_dir = self.aiml_model_dir.text().strip()
        cfg.aiml.temporal_predictor_enabled = self.aiml_temporal_enable.isChecked()
        cfg.aiml.temporal_model_dir = self.aiml_temporal_model_dir.text().strip()

        cfg.camera.width = self.cam_w.value()
        cfg.camera.height = self.cam_h.value()
        cfg.camera.fov_h_deg = self.cam_fov.value()
        cfg.camera.update_rate_hz = float(self.cam_fps.value())
        
        cfg.target.size = self.tgt_size.value()
        cfg.target.intensity = self.tgt_intensity.value()
        cfg.target.speed = self.tgt_speed.value()
        cfg.motion.motion_type = self.tgt_motion.currentText()
        
        # Multi-beacon compositing: if secondary beacons are configured, build beacons list
        if self.secondary_beacons:
            primary = BeaconConfig(
                beacon_id="primary",
                role="primary",
                size=self.tgt_size.value(),
                intensity=self.tgt_intensity.value(),
                speed=self.tgt_speed.value(),
                motion_type=self.tgt_motion.currentText(),
            )
            beacons = [primary]
            for idx, row in enumerate(self.secondary_beacons, start=1):
                sec = BeaconConfig(
                    beacon_id=f"secondary_{idx}",
                    role="secondary",
                    size=row["size"].value(),
                    intensity=row["intensity"].value(),
                    speed=row["speed"].value(),
                    motion_type=self.tgt_motion.currentText(),
                )
                beacons.append(sec)
            cfg.beacons = beacons
        else:
            cfg.beacons = []
        
        cfg.atmospheric.condition = self.dist_atmos.currentText()
        
        noise_text = self.dist_noise.currentText()
        cfg.noise.gaussian_enabled = (noise_text == "GAUSSIAN")
        cfg.noise.sp_enabled = (noise_text == "SALT_AND_PEPPER")
        cfg.noise.poisson_enabled = (noise_text == "POISSON")
        cfg.noise.gaussian_sigma = self.dist_gaussian_sigma.value()
        cfg.noise.sp_density = self.dist_sp_density.value()
        cfg.noise.poisson_scale = self.dist_poisson_scale.value()
        
        # Local contrast clutter
        cfg.local_contrast.enabled = self.dist_local_contrast_enable.isChecked()
        cfg.local_contrast.amplitude = self.dist_local_contrast_amp.value()
        cfg.local_contrast.spatial_scale = self.dist_local_contrast_scale.value()
        cfg.local_contrast.num_blobs = self.dist_local_contrast_blobs.value()
            
        plat_text = self.dist_platform.currentText()
        if plat_text == "NONE":
            cfg.platform_motion.enabled = False
        else:
            cfg.platform_motion.enabled = True
            cfg.platform_motion.motion_type = plat_text
        cfg.platform_motion.max_px_per_frame = self.dist_platform_amp.value()
        
        cfg.jitter.enabled = self.dist_jitter_enable.isChecked()
        cfg.jitter.max_px_per_frame = self.dist_jitter_amp.value()

