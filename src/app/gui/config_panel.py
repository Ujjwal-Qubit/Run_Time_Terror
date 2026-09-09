from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox
from src.app.app_controller import AppController

class ConfigPanel(QWidget):
    def __init__(self, app_controller: AppController):
        super().__init__()
        self.app = app_controller
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
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
        
        # Target Tab
        self.tgt_tab = QWidget()
        tgt_layout = QFormLayout(self.tgt_tab)
        self.tgt_size = QSpinBox(); self.tgt_size.setRange(5, 20); self.tgt_size.setValue(10)
        self.tgt_motion = QComboBox(); self.tgt_motion.addItems(["STRAIGHT_LINE", "CIRCULAR", "FIGURE_8", "RANDOM"])
        tgt_layout.addRow("Size", self.tgt_size)
        tgt_layout.addRow("Motion Type", self.tgt_motion)
        self.tabs.addTab(self.tgt_tab, "Target")
        
        # Disturbances Tab
        self.dist_tab = QWidget()
        dist_layout = QFormLayout(self.dist_tab)
        self.dist_atmos = QComboBox(); self.dist_atmos.addItems(["CLEAR", "HAZE", "FOG", "RAIN", "LOW_LIGHT"])
        self.dist_noise = QComboBox(); self.dist_noise.addItems(["NONE", "SALT_AND_PEPPER", "GAUSSIAN", "POISSON"])
        self.dist_platform = QComboBox(); self.dist_platform.addItems(["NONE", "LINEAR", "CIRCULAR", "RANDOM", "SPIRAL", "FIGURE_8"])
        dist_layout.addRow("Atmosphere", self.dist_atmos)
        dist_layout.addRow("Noise", self.dist_noise)
        dist_layout.addRow("Platform Motion", self.dist_platform)
        self.tabs.addTab(self.dist_tab, "Disturbances")
        
        self.layout.addWidget(self.tabs)
        
    def apply_to_config(self, cfg):
        cfg.camera.width = self.cam_w.value()
        cfg.camera.height = self.cam_h.value()
        cfg.camera.fov_h_deg = self.cam_fov.value()
        cfg.camera.update_rate_hz = float(self.cam_fps.value())
        
        cfg.target.size = self.tgt_size.value()
        cfg.motion.motion_type = self.tgt_motion.currentText()
        
        cfg.atmospheric.condition = self.dist_atmos.currentText()
        
        noise_text = self.dist_noise.currentText()
        cfg.noise.gaussian_enabled = (noise_text == "GAUSSIAN")
        cfg.noise.sp_enabled = (noise_text == "SALT_AND_PEPPER")
        cfg.noise.poisson_enabled = (noise_text == "POISSON")
            
        plat_text = self.dist_platform.currentText()
        if plat_text == "NONE":
            cfg.platform_motion.enabled = False
        else:
            cfg.platform_motion.enabled = True
            cfg.platform_motion.motion_type = plat_text
