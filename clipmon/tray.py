#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi ClipMon - Tray Application (PyInstaller ready)
Replaces start.ps1 with a native Python tray + bundled daemon.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

import pyperclip
import pystray
from PIL import Image, ImageDraw
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ensure daemon.py is importable (both dev and PyInstaller)
_sys_dir = Path(__file__).parent
if str(_sys_dir) not in sys.path:
    sys.path.insert(0, str(_sys_dir))
import daemon

CLIPS_DIR = daemon.CLIPS_DIR
NOTIFY_PATH = daemon.NOTIFY_PATH
LATEST_MD = daemon.LATEST_MD
MANIFEST_PATH = daemon.MANIFEST_PATH


def resource_path(relative_path: str) -> Path:
    """Resolve bundled resource path (PyInstaller or dev)."""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative_path


def load_icon_image():
    """Load bundled icon.ico if available, else generate fallback."""
    try:
        icon_path = resource_path("icon.ico")
        if icon_path.exists():
            return Image.open(str(icon_path))
    except Exception:
        pass
    return create_icon_image()


def create_icon_image():
    """64x64 tray icon"""
    w, h = 64, 64
    img = Image.new('RGB', (w, h), '#1a1a2e')
    dc = ImageDraw.Draw(img)
    dc.rounded_rectangle((4, 4, w - 4, h - 4), radius=12, outline='#00d4aa', width=3)
    dc.text((18, 22), 'KM', fill='#00d4aa')
    return img


def read_recent_tags():
    """Build Recent tags submenu items from manifest"""
    items = []
    if MANIFEST_PATH.exists():
        try:
            lines = [l.strip() for l in MANIFEST_PATH.read_text(encoding='utf-8').split('\n') if l.strip()]
            for line in reversed(lines[-5:]):
                try:
                    obj = json.loads(line)
                    tag = obj.get('id', '')
                    fname = obj.get('filename', '')
                    label = f"{tag}  {fname}"
                    items.append(
                        pystray.MenuItem(
                            label,
                            lambda _icon, _item, _tag=tag: pyperclip.copy(_tag)
                        )
                    )
                except Exception:
                    continue
        except Exception:
            pass
    if not items:
        items = [pystray.MenuItem("(no clips yet)", lambda _icon, _item: None)]
    return items


def build_menu():
    """Dynamic context menu"""
    return pystray.Menu(
        pystray.MenuItem("Recent tags", pystray.Menu(*read_recent_tags())),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open clips folder", lambda _icon, _item: os.startfile(str(CLIPS_DIR))),
        pystray.MenuItem("View latest list", lambda _icon, _item: os.startfile(str(LATEST_MD)) if LATEST_MD.exists() else None),
        pystray.MenuItem("Cleanup old clips", lambda _icon, _item: daemon.cleanup(force_log=False)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", lambda _icon, _item: _icon.stop()),
    )


# Patch pystray Windows backend to support balloon click (NIN_BALLOONUSERCLICK = 0x405)
_original_on_notify = pystray._win32.Icon._on_notify

def _patched_on_notify(self, wparam, lparam):
    if lparam == 0x405:  # NIN_BALLOONUSERCLICK
        self._notify_action()
    else:
        _original_on_notify(self, wparam, lparam)

pystray._win32.Icon._on_notify = _patched_on_notify


class ClipMonIcon(pystray.Icon):
    """Custom tray icon with balloon-click copy support"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_tag = None

    def _notify_action(self):
        """Called when user clicks the notification balloon (Windows)"""
        if self.last_tag:
            try:
                pyperclip.copy(self.last_tag)
            except Exception:
                pass


class NotifyHandler(FileSystemEventHandler):
    """Watch .notify file for balloon tips"""
    def __init__(self, icon_ref):
        self.icon_ref = icon_ref
        self._last_notify = ""
        self._last_time = 0

    def on_modified(self, event):
        p = Path(event.src_path)
        if p.name == ".notify" and p.parent == CLIPS_DIR:
            try:
                content = NOTIFY_PATH.read_text(encoding='utf-8').strip()
                if not content:
                    return
                # Deduplicate: skip if same content within 2 seconds
                now = time.time()
                if content == self._last_notify and now - self._last_time < 2:
                    return
                self._last_notify = content
                self._last_time = now
                parts = content.split(None, 1)
                tag = parts[0]
                fname = parts[1] if len(parts) > 1 else ""
                self.icon_ref.last_tag = tag
                self.icon_ref.notify(f"Saved {tag}\n{fname}", "Kimi ClipMon")
            except Exception:
                pass


class ManifestHandler(FileSystemEventHandler):
    """Refresh menu when manifest changes"""
    def __init__(self, icon_ref):
        self.icon_ref = icon_ref

    def on_modified(self, event):
        p = Path(event.src_path)
        if p.name == "manifest.jsonl" and p.parent == CLIPS_DIR:
            try:
                self.icon_ref.menu = build_menu()
                if hasattr(self.icon_ref, 'update_menu'):
                    self.icon_ref.update_menu()
            except Exception:
                pass


def main():
    # Start daemon in background thread
    daemon.running = True
    d_thread = threading.Thread(target=daemon.watch_main, daemon=True)
    d_thread.start()

    # Create tray icon
    icon = ClipMonIcon(
        "KimiClipMon",
        load_icon_image(),
        "Kimi ClipMon",
        menu=build_menu()
    )

    # Left-click = view latest list
    def on_click(_icon, _item):
        if LATEST_MD.exists():
            os.startfile(str(LATEST_MD))
    icon.on_click = on_click

    # Watch .notify and manifest.jsonl for updates
    observer = Observer()
    observer.schedule(NotifyHandler(icon), str(CLIPS_DIR), recursive=False)
    observer.schedule(ManifestHandler(icon), str(CLIPS_DIR), recursive=False)
    observer.start()

    try:
        icon.run()
    finally:
        # Graceful shutdown
        daemon.running = False
        observer.stop()
        observer.join()
        d_thread.join(timeout=5)


if __name__ == "__main__":
    main()
