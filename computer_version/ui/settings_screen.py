from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QMessageBox, QFrame,
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

        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.app.show_home)
        top.addWidget(back_btn)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

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

        root.addWidget(form_frame)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn, alignment=Qt.AlignRight)
        root.addStretch()

    def _load(self):
        settings = self.app.db.get_all_settings()
        self._goal_edit.setText(settings.get("daily_goal", "20"))
        self._notify_edit.setText(settings.get("notify_time", "18:00"))

    def _save(self):
        goal = self._goal_edit.text().strip()
        if goal and not goal.isdigit():
            QMessageBox.warning(self, "Validation",
                                "Daily goal must be a whole number.")
            return
        self.app.db.set_setting("daily_goal", goal)
        self.app.db.set_setting("notify_time", self._notify_edit.text().strip())
        QMessageBox.information(self, "Saved", "Settings saved.")
        self.app.show_home()
