from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QSlider, QMessageBox, QFrame,
)
from PyQt5.QtCore import Qt
class SettingsScreen(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.app.show_home)
        top.addWidget(back_btn)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        # Form
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.StyledPanel)
        form = QFormLayout(form_frame)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self._goal_edit = QLineEdit()
        self._goal_edit.setFixedWidth(100)
        form.addRow("Daily goal (cards):", self._goal_edit)

        self._notify_edit = QLineEdit()
        self._notify_edit.setFixedWidth(100)
        form.addRow("Notify at (HH:MM):", self._notify_edit)

        api_row = QHBoxLayout()
        self._api_edit = QLineEdit()
        self._api_edit.setFixedWidth(400)
        self._api_edit.setEchoMode(QLineEdit.Password)
        api_row.addWidget(self._api_edit)
        show_btn = QPushButton("Show")
        show_btn.setCheckable(True)
        show_btn.toggled.connect(
            lambda checked: self._api_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_row.addWidget(show_btn)
        api_row.addStretch()
        form.addRow("Claude API key:", api_row)

        decay_row = QHBoxLayout()
        self._decay_slider = QSlider(Qt.Horizontal)
        self._decay_slider.setRange(0, 200)
        self._decay_slider.setFixedWidth(200)
        self._decay_label = QLabel("5.0")
        self._decay_slider.valueChanged.connect(
            lambda v: self._decay_label.setText(f"{v / 10:.1f}")
        )
        decay_row.addWidget(self._decay_slider)
        decay_row.addWidget(self._decay_label)
        decay_row.addStretch()
        form.addRow("Decay rate (pts/day):", decay_row)

        root.addWidget(form_frame)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn, alignment=Qt.AlignRight)
        root.addStretch()

    def _load(self):
        settings = self.app.db.get_all_settings()
        self._goal_edit.setText(settings.get("daily_goal", "10"))
        self._notify_edit.setText(settings.get("notify_time", "09:00"))
        self._api_edit.setText(settings.get("claude_api_key", ""))
        decay = float(settings.get("decay_rate", "5.0"))
        self._decay_slider.setValue(int(decay * 10))
        self._decay_label.setText(f"{decay:.1f}")

    def _save(self):
        goal = self._goal_edit.text().strip()
        if goal and not goal.isdigit():
            QMessageBox.warning(self, "Validation",
                                "Daily goal must be a whole number.")
            return
        self.app.db.set_setting("daily_goal", goal)
        self.app.db.set_setting("notify_time", self._notify_edit.text().strip())
        self.app.db.set_setting("claude_api_key", self._api_edit.text().strip())
        self.app.db.set_setting("decay_rate",
                                f"{self._decay_slider.value() / 10:.1f}")
        QMessageBox.information(self, "Saved", "Settings saved.")
        self.app.show_home()
