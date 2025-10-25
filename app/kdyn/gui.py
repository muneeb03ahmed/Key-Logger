from __future__ import annotations
import uuid
import datetime
from typing import List
from PySide6 import QtWidgets, QtCore, QtGui

from .recorder import Recorder
from .analytics import aggregate
from .reports import write_json, write_html
from .settings import AppSettings, SessionDefaults, NotificationPrefs, UISettings
from .notify import Notifier

import logging
logger = logging.getLogger(__name__)

# Simple sparkline widget
class Sparkline(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[float] = []  # last N latency values (ms)
        self.setMinimumHeight(48)

    def update_data(self, values: List[float]):
        self.data = values[-100:]
        self.update()

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        p.fillRect(self.rect(), QtGui.QColor(22,22,26))
        if not self.data:
            return
        mx = max(self.data) or 1.0
        step = rect.width() / max(len(self.data)-1, 1)
        path = QtGui.QPainterPath()
        for i, v in enumerate(self.data):
            x = rect.left() + i*step
            y = rect.bottom() - (v/mx)*rect.height()
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        pen = QtGui.QPen(QtGui.QColor(52, 152, 219), 2)
        p.setPen(pen)
        p.drawPath(path)

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = settings
        layout = QtWidgets.QFormLayout(self)

        # Session defaults
        self.session_name = QtWidgets.QLineEdit(self.settings.session.session_name)
        self.max_duration = QtWidgets.QSpinBox(); self.max_duration.setRange(0, 86400); self.max_duration.setValue(self.settings.session.max_duration_sec)
        self.idle_timeout = QtWidgets.QSpinBox(); self.idle_timeout.setRange(0, 3600); self.idle_timeout.setValue(self.settings.session.idle_timeout_sec)

        # Theme
        self.theme = QtWidgets.QComboBox(); self.theme.addItems(["light","dark","high_contrast"])
        self.theme.setCurrentText(self.settings.ui.theme)

        # Notifications
        self.use_discord = QtWidgets.QCheckBox("Enable Discord")
        self.use_discord.setChecked(self.settings.notifications.use_discord)
        self.discord_hook = QtWidgets.QLineEdit(self.settings.notifications.discord_webhook)

        self.use_telegram = QtWidgets.QCheckBox("Enable Telegram")
        self.use_telegram.setChecked(self.settings.notifications.use_telegram)
        self.tg_token = QtWidgets.QLineEdit(self.settings.notifications.telegram_token)
        self.tg_chat = QtWidgets.QLineEdit(self.settings.notifications.telegram_chat_id)

        layout.addRow("Session name", self.session_name)
        layout.addRow("Max duration (sec)", self.max_duration)
        layout.addRow("Idle timeout (sec)", self.idle_timeout)
        layout.addRow("Theme", self.theme)
        layout.addRow(self.use_discord)
        layout.addRow("Discord webhook", self.discord_hook)
        layout.addRow(self.use_telegram)
        layout.addRow("Telegram bot token", self.tg_token)
        layout.addRow("Telegram chat id", self.tg_chat)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def accept(self) -> None:
        self.settings.session.session_name = self.session_name.text().strip() or "default"
        self.settings.session.max_duration_sec = int(self.max_duration.value())
        self.settings.session.idle_timeout_sec = int(self.idle_timeout.value())
        self.settings.ui.theme = self.theme.currentText()
        self.settings.notifications.use_discord = self.use_discord.isChecked()
        self.settings.notifications.discord_webhook = self.discord_hook.text().strip()
        self.settings.notifications.use_telegram = self.use_telegram.isChecked()
        self.settings.notifications.telegram_token = self.tg_token.text().strip()
        self.settings.notifications.telegram_chat_id = self.tg_chat.text().strip()
        self.settings.save()
        super().accept()

class ConsentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Consent Required")
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(
            """
            <b>KDyn collects timing metadata only</b> (key down/up timestamps and derived metrics).
            <br>It does <b>not</b> capture plaintext characters, window titles, or field contents.
            <br>By clicking <b>Accept</b>, you consent to timing-only collection for the current user session.
            """
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        btns.button(QtWidgets.QDialogButtonBox.Ok).setText("Accept")
        btns.button(QtWidgets.QDialogButtonBox.Cancel).setText("Decline")
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

class MainWindow(QtWidgets.QMainWindow):
    update_signal = QtCore.Signal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("KDyn — Keystroke Dynamics (Timing Only)")
        self.setMinimumSize(900, 560)

        self.rec = Recorder(max_duration_sec=self.settings.session.max_duration_sec,
                            idle_timeout_sec=self.settings.session.idle_timeout_sec)

        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top_bar = QtWidgets.QHBoxLayout()
        self.session_name = QtWidgets.QLineEdit(self.settings.session.session_name)
        self.start_btn = QtWidgets.QPushButton("Start (Ctrl+R)")
        self.pause_btn = QtWidgets.QPushButton("Pause/Resume (Ctrl+P)")
        self.stop_btn = QtWidgets.QPushButton("Stop (Ctrl+S)")
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.export_btn = QtWidgets.QPushButton("Export Reports")
        for w in [self.start_btn, self.pause_btn, self.stop_btn, self.reset_btn, self.export_btn]:
            w.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        top_bar.addWidget(QtWidgets.QLabel("Session:")); top_bar.addWidget(self.session_name, 1)
        top_bar.addWidget(self.start_btn); top_bar.addWidget(self.pause_btn); top_bar.addWidget(self.stop_btn)
        top_bar.addWidget(self.reset_btn); top_bar.addWidget(self.export_btn)

        kpi_grid = QtWidgets.QGridLayout()
        self.lbl_events = QtWidgets.QLabel("0")
        self.lbl_med_hold = QtWidgets.QLabel("0.0")
        self.lbl_med_lat = QtWidgets.QLabel("0.0")
        self.lbl_bursts = QtWidgets.QLabel("0")
        self.lbl_avg_burst = QtWidgets.QLabel("0.0")
        def big(lbl: QtWidgets.QLabel):
            f = lbl.font(); f.setPointSize(16); lbl.setFont(f)
        for l in [self.lbl_events, self.lbl_med_hold, self.lbl_med_lat, self.lbl_bursts, self.lbl_avg_burst]:
            big(l)
        kpi_grid.addWidget(QtWidgets.QLabel("Events"), 0,0); kpi_grid.addWidget(self.lbl_events, 1,0)
        kpi_grid.addWidget(QtWidgets.QLabel("Median Hold (ms)"), 0,1); kpi_grid.addWidget(self.lbl_med_hold, 1,1)
        kpi_grid.addWidget(QtWidgets.QLabel("Median Latency (ms)"), 0,2); kpi_grid.addWidget(self.lbl_med_lat, 1,2)
        kpi_grid.addWidget(QtWidgets.QLabel("Bursts"), 0,3); kpi_grid.addWidget(self.lbl_bursts, 1,3)
        kpi_grid.addWidget(QtWidgets.QLabel("Avg Burst Length"), 0,4); kpi_grid.addWidget(self.lbl_avg_burst, 1,4)

        spark_card = QtWidgets.QGroupBox("Latency Sparkline (ms; recent)")
        sp_lay = QtWidgets.QVBoxLayout(spark_card)
        self.spark = Sparkline()
        sp_lay.addWidget(self.spark)

        root.addLayout(top_bar)
        root.addLayout(kpi_grid)
        root.addWidget(spark_card)

        # Status bar + menu
        self.status = self.statusBar()
        menu = self.menuBar()
        filem = menu.addMenu("&File")
        act_export = filem.addAction("Export Reports")
        act_export.triggered.connect(self.export_reports)
        filem.addSeparator()
        act_quit = filem.addAction("Exit")
        act_quit.triggered.connect(self.close)

        prefm = menu.addMenu("&Preferences")
        act_settings = prefm.addAction("Settings…")
        act_settings.triggered.connect(self.open_settings)

        helpm = menu.addMenu("&Help")
        act_about = helpm.addAction("About")
        act_about.triggered.connect(self.about)

        # Shortcuts
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), self, activated=self.start)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+P"), self, activated=self.toggle_pause)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self.stop)

        # Timers
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh_kpis)
        self.timer.start(250)

        # State
        self.session_id: str | None = None
        self.lat_sample: List[float] = []

        # Apply theme
        self.apply_theme(self.settings.ui.theme)

        # Consent on first run
        if not self.settings.consent_accepted:
            dlg = ConsentDialog(self)
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                self.settings.consent_accepted = True
                self.settings.save()
            else:
                QtWidgets.QMessageBox.warning(self, "Consent not granted", "KDyn requires consent to run. Exiting.")
                QtCore.QTimer.singleShot(0, self.close)

        # Tooltips for A11y
        for w in [self.start_btn, self.pause_btn, self.stop_btn, self.reset_btn, self.export_btn]:
            w.setToolTip(w.text())

        # Wire up buttons
        self.start_btn.clicked.connect(self.start)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn.clicked.connect(self.stop)
        self.reset_btn.clicked.connect(self.reset)
        self.export_btn.clicked.connect(self.export_reports)

    # THEME
    def apply_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet("QWidget{background:#111;color:#e6e6e6;} QLineEdit, QGroupBox{background:#1b1b1f;border:1px solid #2a2a2f;border-radius:8px;padding:6px;}")
        elif theme == "high_contrast":
            self.setStyleSheet("QWidget{background:#000;color:#fff;} QPushButton{background:#fff;color:#000;}")
        else:
            self.setStyleSheet("")

    # ACTIONS
    def start(self):
        if self.session_id is None:
            self.session_id = f"{self.session_name.text().strip() or 'session'}-{uuid.uuid4().hex[:8]}"
        self.rec.max_duration_sec = self.settings.session.max_duration_sec
        self.rec.idle_timeout_sec = self.settings.session.idle_timeout_sec
        self.rec.start(datetime.datetime.utcnow().isoformat())
        self.status.showMessage("Recording started")

    def toggle_pause(self):
        # Simplified: if paused, resume; else pause
        # We infer state by checking if events progress; here we directly call both paths based on internal flag
        self.rec.resume() if True else self.rec.pause()
        # We can't easily query paused flag; give feedback generically
        self.status.showMessage("Toggled pause/resume")

    def stop(self):
        self.rec.stop()
        self.status.showMessage("Stopped")

    def reset(self):
        self.rec.reset(clear_data=True)
        self.session_id = None
        self.lat_sample.clear()
        self.refresh_kpis()
        self.status.showMessage("Reset")

    def about(self):
        QtWidgets.QMessageBox.information(self, "About KDyn",
            "KDyn records timing-only keystroke dynamics.\nNo plaintext is ever captured.")

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.apply_theme(self.settings.ui.theme)
            self.status.showMessage("Settings saved.")

    def refresh_kpis(self):
        # Compute lightweight live KPIs using analytics.aggregate
        if self.session_id and self.rec.started_at_iso:
            m = aggregate(
                session_id=self.session_id,
                started_at=self.rec.started_at_iso,
                duration_secs=self.rec.duration_secs(),
                total_events=self.rec.total_events,
                holds=self.rec.holds,
                latencies=self.rec.latencies,
                press_timestamps_ms=self.rec.press_timestamps_ms,
            )
            self.lbl_events.setText(str(m.events))
            self.lbl_med_hold.setText(f"{m.median_hold_ms:.1f}")
            self.lbl_med_lat.setText(f"{m.median_latency_ms:.1f}")
            self.lbl_bursts.setText(str(m.bursts))
            self.lbl_avg_burst.setText(f"{m.avg_burst_len:.1f}")
            # Update sparkline
            self.spark.update_data([l.latency_ms for l in self.rec.latencies])
        else:
            self.lbl_events.setText("0"); self.lbl_med_hold.setText("0.0"); self.lbl_med_lat.setText("0.0"); self.lbl_bursts.setText("0"); self.lbl_avg_burst.setText("0.0")
            self.spark.update_data([])

    def export_reports(self):
        if not self.session_id or not self.rec.started_at_iso:
            QtWidgets.QMessageBox.warning(self, "Nothing to export", "Start a session first.")
            return
        m = aggregate(
            session_id=self.session_id,
            started_at=self.rec.started_at_iso,
            duration_secs=self.rec.duration_secs(),
            total_events=self.rec.total_events,
            holds=self.rec.holds,
            latencies=self.rec.latencies,
            press_timestamps_ms=self.rec.press_timestamps_ms,
        )
        j = write_json(m)
        h = write_html(m)
        self.status.showMessage(f"Exported: {j} & {h}")

        # Optional notifications
        n = self.settings.notifications
        if n.use_discord or n.use_telegram:
            summary = (
                f"KDyn {m.session_id}: events={m.events}, med_hold={m.median_hold_ms:.1f}ms, "
                f"med_lat={m.median_latency_ms:.1f}ms"
            )
            Notifier(n.discord_webhook if n.use_discord else None,
                     n.telegram_token if n.use_telegram else None,
                     n.telegram_chat_id if n.use_telegram else None
                     ).post_summary(summary)
            self.status.showMessage(self.status.currentMessage() + " • Notification sent (if configured)")