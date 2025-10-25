# KDyn — Keystroke Dynamics (Timing‑Only) GUI Tool

KDyn is a privacy‑first Windows desktop app that records **only timing metadata** of keystrokes (key down/up timestamps, holds, and inter‑key latencies). It **never** stores plaintext characters, window titles, or field contents. Generate JSON + HTML reports, and optionally ship a short summary to Telegram or Discord.

## Features
- Timing‑only collection (no plaintext)
- Start/Pause/Resume/Stop/Reset controls
- Live KPIs: events, median hold/latency, bursts & avg burst length
- Optional sparkline of recent latencies
- JSON + HTML reports in `./reports/<session_id>.{json,html}`
- Optional Discord webhook / Telegram bot summaries
- Consent modal on first launch; settings in `%APPDATA%/KDyn/config.json`
- Light/Dark/High‑contrast themes; keyboard shortcuts

## Install & Run (Dev)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app\main.py
````

## Build Single EXE (PyInstaller)

```powershell
# Optional: place an icon at build/icon.ico
pyinstaller -y -F -n KDyn --add-data "app\kdyn\resources.qrc;kdyn" app\main.py
# or use the provided spec for more control
pyinstaller -y build\build.spec
```

> **Performance targets:** idle CPU < 2%, memory < 120 MB on Windows 10/11. No admin, no kernel hooks.

## Privacy Statement

KDyn captures only anonymized virtual‑key (VK) codes and timestamps to compute timing metrics. **Plaintext keystrokes are never captured or persisted.**

## Settings

* `%APPDATA%/KDyn/config.json` stores consent, theme, session defaults, and optional notification settings.

## Notifications (Optional)

* **Discord:** set `use_discord=true` and `discord_webhook` in Settings.
* **Telegram:** set `use_telegram=true`, and provide `telegram_token` + `telegram_chat_id`.

## Tests

```powershell
venv\Scripts\activate
pytest -q
```

## Packaging & Code Signing (Optional)

After PyInstaller build, sign `KDyn.exe` with your code‑signing certificate using `signtool.exe`.
