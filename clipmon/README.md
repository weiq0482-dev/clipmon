# Kimi ClipMon — Screenshot Auto-Numbering for Kimi CLI

> **The problem it solves**: Sending screenshots to AI inside a terminal chat should not require digging through folders, memorizing filenames, or typing long paths.

[中文文档](README.zh-CN.md)

---

## What it does in one sentence

Kimi ClipMon is a Windows system-tray utility that **automatically assigns incrementing `@N` tags to your screenshots**. Inside [Kimi CLI](https://www.kimi.com) (or any terminal chat that supports the `@N` image-reference syntax), typing `@3` instantly refers to your 3rd screenshot — no filenames, no paths, no manual uploads.

> **Scope note**: `@N` is a Kimi CLI-specific image-reference convention. It will not work in Claude Code, Cursor, or other assistants.

---

## Before vs After

| Step | Without this tool | With Kimi ClipMon |
|---|---|---|
| Take screenshot | `Win+Shift+S` | `Win+Shift+S` (same) |
| Save | Manually save and name the file | **Auto-saved, no action needed** |
| Locate | Browse folders, copy the path | **No lookup; auto-numbered** |
| Send to AI | `/path/to/screenshot_20260502_094812.png` | **`@3`** |
| Reference an older shot | Re-browse and re-copy path | **Just type `@1` or `@2`** |

**We eliminate the entire context-switching cost between screenshot and chat.**

---

## Download & Run (Recommended)

1. Download `KimiClipMon.exe` from the [latest Release](https://github.com/weiq0482-dev/clipmon/releases/latest)
2. Double-click to run — a tray icon appears
3. Take a screenshot — a balloon pops up: `Saved @3`
4. **Click the balloon** — `@3` is copied to your clipboard
5. Paste into Kimi CLI with `Ctrl+V`

> On first run the app auto-creates `~/.kimi-cli/clips/` and adds itself to Windows startup.

---

## Developer / Source Install

```powershell
git clone https://github.com/weiq0482-dev/clipmon.git
cd clipmon
.\setup.bat          # One-click install + auto-start
```

Or manually:
```powershell
pip install pillow pystray watchdog pyperclip
python tray.py       # Tray mode (recommended)
python daemon.py     # Headless mode (no tray)
```

---

## How to use

### Method 1: Clipboard bridge (default)

Works with any screenshot tool (Windows Snipping Tool, WeChat `Alt+A`, QQ, Snipaste):

```
You take a screenshot → image lands on clipboard
                           ↓
                Clipboard bridge auto-saves it
                           ↓
                Tray balloon: Saved @3
                           ↓
                Click balloon to copy @3
                           ↓
                Paste into Kimi CLI:

                    What does this error mean @3
```

**Key guarantee: read-only clipboard access. We never write to your clipboard, so copy/paste in any other app is unaffected.**

### Method 2: Manual drop

Drag any image into `~/.kimi-cli/clips/inbox/` — it gets numbered and notified just the same.

---

## Tray Menu

Right-click the tray icon:

| Menu item | Function |
|---|---|
| Recent tags | Last 5 `@N` entries (click to copy) |
| Open clips folder | Open the screenshots directory |
| View latest list | Open `latest.md` with all tags |
| Cleanup old clips | Manually purge screenshots older than 7 days |
| Exit | Quit the app |

Left-click the tray icon: opens `latest.md` directly.

---

## Numbering Rules

- **`@1`, `@2`, `@3` … globally incrementing**, persisted in `manifest.jsonl`, survive reboots
- **Duplicate protection**: clipboard images are deduplicated by MD5
- **Auto-cleanup**: keeps max 50 clips, deletes anything older than 7 days

---

## Data Directory

```
C:\Users\<username>\.kimi-cli\clips\
├── inbox\                        # Drop images here to process manually
├── 20260502_094812_345.png      # Auto-saved screenshot
├── manifest.jsonl               # Persistent tag → filename mapping
├── latest.md                    # Human-readable index of last 30 clips
└── daemon.log                   # Runtime log
```

---

## FAQ

**Q: Do I have to put screenshots into inbox manually?**
A: No. The clipboard bridge handles system screenshots, WeChat, QQ, etc. The inbox folder is only for manual drag-and-drop.

**Q: I took 5 screenshots; how do I refer back to the 2nd one?**
A: Left-click the tray icon to open `latest.md`, or use the Recent tags menu.

**Q: Can tag numbers collide or skip?**
A: No. Tags are strictly monotonic based on the persistent `manifest.jsonl` file. They only reset if you manually delete that file.

**Q: Will this break my normal copy/paste?**
A: Absolutely not. The app **only reads** images from the clipboard to save locally. It **never writes** to the clipboard. Text copies, file copies, and everything else work normally.

**Q: How do I fully stop it?**
A: Right-click tray icon → Exit. If something is stuck, end `KimiClipMon.exe` in Task Manager.

---

## License

MIT License — see [LICENSE](LICENSE) file.
