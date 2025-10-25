from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
import os
from typing import Optional

APP_DIR = Path(os.getenv("APPDATA", ".")) / "KDyn"
CONFIG_PATH = APP_DIR / "config.json"

@dataclass
class NotificationPrefs:
    use_discord: bool = False
    discord_webhook: str = ""
    use_telegram: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""

@dataclass
class UISettings:
    theme: str = "light"  # "light", "dark", "high_contrast"

@dataclass
class SessionDefaults:
    session_name: str = "default"
    max_duration_sec: int = 120
    idle_timeout_sec: int = 10

@dataclass
class AppSettings:
    consent_accepted: bool = False
    notifications: NotificationPrefs = field(default_factory=NotificationPrefs)
    ui: UISettings = field(default_factory=UISettings)
    session: SessionDefaults = field(default_factory=SessionDefaults)

    @staticmethod
    def load() -> "AppSettings":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                # Manual hydrate to keep defaults for missing keys
                s = AppSettings()
                s.consent_accepted = bool(data.get("consent_accepted", s.consent_accepted))
                n = data.get("notifications", {})
                s.notifications = NotificationPrefs(
                    use_discord=bool(n.get("use_discord", False)),
                    discord_webhook=str(n.get("discord_webhook", "")),
                    use_telegram=bool(n.get("use_telegram", False)),
                    telegram_token=str(n.get("telegram_token", "")),
                    telegram_chat_id=str(n.get("telegram_chat_id", "")),
                )
                u = data.get("ui", {})
                s.ui = UISettings(theme=str(u.get("theme", s.ui.theme)))
                sess = data.get("session", {})
                s.session = SessionDefaults(
                    session_name=str(sess.get("session_name", s.session.session_name)),
                    max_duration_sec=int(sess.get("max_duration_sec", s.session.max_duration_sec)),
                    idle_timeout_sec=int(sess.get("idle_timeout_sec", s.session.idle_timeout_sec)),
                )
                return s
            except Exception:
                pass
        return AppSettings()

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
