#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi ClipMon - Windows Screenshot Monitor (Watchdog Mode)
目录监视模式：完全不监听剪贴板，监视 clips/inbox/ 文件夹。
将截图文件保存到 inbox 目录，守护进程自动分配编号并归档。
"""

import hashlib
import io
import json
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageGrab

# ── 配置 ───────────────────────────────────────────────
CLIPS_DIR = Path.home() / ".kimi-cli" / "clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

INBOX_DIR = CLIPS_DIR / "inbox"
INBOX_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = CLIPS_DIR / "manifest.jsonl"
LATEST_MD = CLIPS_DIR / "latest.md"
LOG_PATH = CLIPS_DIR / "daemon.log"
NOTIFY_PATH = CLIPS_DIR / ".notify"

MAX_CLIPS = 50
MAX_DAYS = 7
WATCH_INTERVAL = 1.0  # 目录轮询间隔（秒）

# 支持的图片格式
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# ── 全局状态 ───────────────────────────────────────────
running = True


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_all_entries() -> list[dict]:
    entries: list[dict] = []
    if not MANIFEST_PATH.exists():
        return entries
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def update_latest_md(entries: list[dict]):
    lines = [
        "# 最近截图\n",
        "| 编号 | 文件名 | 时间 |",
        "|------|--------|------|",
    ]
    for e in entries[-30:]:
        idx = e.get("id", "?")
        lines.append(f"| `{idx}` | `{e['filename']}` | {e['time']} |")
    lines.append(f"\n**目录**: `{CLIPS_DIR}`")
    lines.append(f"\n**总数**: {len(entries)} 张")
    lines.append(f"\n**保留策略**: 最多 {MAX_CLIPS} 张 / {MAX_DAYS} 天")
    lines.append("\n---")
    lines.append("\n**引用方式**: 在 Kimi CLI 中直接输入 `@N` 即可引用对应图片")
    LATEST_MD.write_text("\n".join(lines), encoding="utf-8")


def save_manifest(entry: dict):
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def rewrite_manifest(entries: list[dict]):
    if entries:
        MANIFEST_PATH.write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
            encoding="utf-8",
        )
    else:
        MANIFEST_PATH.write_text("", encoding="utf-8")


def notify(info: str):
    try:
        NOTIFY_PATH.write_text(info, encoding="utf-8")
    except Exception:
        pass


def is_image_file(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTS


def cleanup(force_log: bool = True) -> int:
    entries = read_all_entries()
    manifest_paths = {e["path"] for e in entries}

    now = datetime.now()
    cutoff = now - timedelta(days=MAX_DAYS)
    remove_paths: set[str] = set()
    sorted_entries = sorted(entries, key=lambda x: x.get("time", ""))

    for e in sorted_entries:
        try:
            t = datetime.strptime(e["time"], "%Y-%m-%d %H:%M:%S")
            if t < cutoff:
                remove_paths.add(e["path"])
        except (ValueError, KeyError):
            pass

    remaining = [e for e in sorted_entries if e["path"] not in remove_paths]
    if len(remaining) > MAX_CLIPS:
        excess = len(remaining) - MAX_CLIPS
        for e in remaining[:excess]:
            remove_paths.add(e["path"])

    removed = 0
    for p in remove_paths:
        try:
            Path(p).unlink(missing_ok=True)
            removed += 1
        except Exception as e:
            log(f"Cleanup delete error: {e}")

    new_entries = [e for e in entries if e["path"] not in remove_paths]
    rewrite_manifest(new_entries)
    update_latest_md(new_entries)

    # Clean up orphan PNGs not tracked in manifest
    for f in CLIPS_DIR.glob("*.png"):
        if str(f) not in manifest_paths:
            try:
                f.unlink(missing_ok=True)
                removed += 1
            except Exception as e:
                log(f"Cleanup orphan error: {e}")

    if force_log:
        log(f"Cleanup: removed {removed} clip(s), {len(new_entries)} remaining")
    return removed


def process_inbox_file(src_path: Path) -> tuple[Path, str] | None:
    """处理 inbox 中的单个截图文件"""
    try:
        img = Image.open(src_path)

        existing = read_all_entries()
        if existing:
            clip_id = max(e.get("num", 0) for e in existing) + 1
        else:
            clip_id = 1
        clip_tag = f"@{clip_id}"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{ts}.png"
        dst_path = CLIPS_DIR / filename
        img.save(dst_path, "PNG")

        # 删除源文件
        src_path.unlink()

        entry = {
            "id": clip_tag,
            "num": clip_id,
            "path": str(dst_path),
            "filename": filename,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hash": hashlib.md5(dst_path.read_bytes()).hexdigest(),
        }

        save_manifest(entry)
        entries = read_all_entries()
        update_latest_md(entries)
        notify(f"{clip_tag} {filename}")

        log(f"Saved: {filename} -> {clip_tag}")
        cleanup()

        return dst_path, clip_tag

    except Exception as e:
        log(f"Error processing {src_path.name}: {e}")
        return None


def clipboard_bridge():
    """剪贴板桥接：检测剪贴板图片，保存到 inbox，不修改剪贴板内容"""
    last_hash: str | None = None
    poll_interval = 2.5

    log("Clipboard bridge started (read-only)")

    while running:
        try:
            result = ImageGrab.grabclipboard()
            if isinstance(result, Image.Image):
                buf = io.BytesIO()
                result.save(buf, format="PNG")
                h = hashlib.md5(buf.getvalue()).hexdigest()
                if h != last_hash:
                    last_hash = h
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    filename = f"{ts}.png"
                    filepath = INBOX_DIR / filename
                    result.save(filepath, "PNG")
                    log(f"Clipboard bridge: saved {filename}")
            elif isinstance(result, list):
                # 剪贴板里是文件列表，忽略
                pass
        except Exception as e:
            log(f"Clipboard bridge error: {e}")

        time.sleep(poll_interval)


def watch_main():
    """目录监视模式主循环"""
    log("=" * 50)
    log("Kimi ClipMon started (WATCHDOG MODE)")
    log(f"Inbox:  {INBOX_DIR}")
    log(f"Clips:  {CLIPS_DIR}")
    log(f"Tip: Save screenshots to inbox folder, click tray icon to view tags")
    log("=" * 50)

    # 启动剪贴板桥接线程（读取剪贴板图片并保存到 inbox，不修改剪贴板）
    bridge_thread = threading.Thread(target=clipboard_bridge, daemon=True)
    bridge_thread.start()

    # 初始已知文件集合
    known_files = {p.name for p in INBOX_DIR.iterdir() if p.is_file()}

    try:
        while running:
            current_files = {p.name for p in INBOX_DIR.iterdir() if p.is_file()}
            new_files = current_files - known_files

            for name in sorted(new_files):
                if not is_image_file(name):
                    continue
                src = INBOX_DIR / name
                # 等待文件写入完成（避免处理到半成品）
                time.sleep(0.5)
                if src.exists():
                    process_inbox_file(src)

            known_files = current_files
            time.sleep(WATCH_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        log("Kimi ClipMon stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        n = cleanup(force_log=False)
        print(f"Cleaned up {n} old clip(s).")
    else:
        watch_main()
