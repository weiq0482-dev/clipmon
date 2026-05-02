# Kimi ClipMon — 截图自动编号，Kimi CLI 里一句话贴图

> **解决的核心痛点**：在 Kimi CLI 命令行里给 AI 发截图，再也不用翻文件夹、记文件名、打长路径了。

[English](README.md)

## 先看效果

```
你: 这个报错什么意思 @3
Kimi: 这是 ModuleNotFoundError，缺少依赖...

你: 对比下 @1 和 @2 的配置差异
Kimi: @1 里数据库 host 是 localhost，@2 里改成了 192.168...

你: 先看 @1 正常状态，再看 @3 报错，帮我排查
Kimi: 从 @1 到 @3，变化在于第三方库版本升级...
```

**全程你只需要记住 `@1`、`@2`、`@3` 这三个字符。**

---

## 没有这工具之前，你发截图有多麻烦？

| 步骤 | 传统方式 | Kimi ClipMon |
|---|---|---|
| 截图 | `Win+Shift+S` | `Win+Shift+S`（一样） |
| 保存 | 手动另存为，起文件名 | **自动保存，不用管** |
| 找图 | 翻文件夹，复制路径 | **不用找，系统自动编号** |
| 发图 | `/path/to/screenshot_20260502_094812.png` | **`@3`** |
| 引用历史图 | 重新找文件，再贴路径 | **直接打 `@1` 或 `@2`** |

**省掉的不是一步两步，是截图→发图之间全部的上下文切换成本。**

---

## 一句话总结

Kimi ClipMon 是 Windows 系统托盘常驻工具，**自动读取你剪贴板里的截图、分配递增编号 `@N`**。在 Kimi CLI 对话中，输入 `@3` 即可引用第 3 张图，无需文件名、无需路径、无需手动上传。

> **专用性说明**：`@N` 是 Kimi CLI 的图片引用语法，在其他 AI 助手（如 Claude Code、Cursor）中无法识别。

---

## 下载直接用（推荐）

1. 从 [Releases](https://github.com/weiq0482-dev/clipmon/releases/latest) 下载 `KimiClipMon.exe`
2. 双击运行，右下角托盘出现图标
3. 正常截图，托盘弹出气泡 `Saved @3`
4. **点击气泡** → `@3` 已复制到剪贴板
5. 在 Kimi CLI 中 `Ctrl+V` 粘贴 `@3`

> 首次运行会自动创建 `~/.kimi-cli/clips/` 目录和开机自启动。

---

## 开发者/源码安装

```powershell
git clone https://github.com/weiq0482-dev/clipmon.git
cd clipmon
.\setup.bat          # 一键安装 + 开机自启
```

或手动：
```powershell
pip install pillow pystray watchdog pyperclip
python tray.py       # 托盘模式（推荐）
python daemon.py     # 纯后台模式（无托盘）
```

---

## 使用方式

### 方式一：剪贴板自动桥接（最常用）

任何截图工具都行（系统截图、微信 `Alt+A`、QQ、Snipaste）：

```
你截图 → 图片进入剪贴板
           ↓
    剪贴板桥接自动保存
           ↓
    托盘气泡：Saved @3
           ↓
    点击气泡复制 @3
           ↓
    在 Kimi CLI 粘贴：

        这个报错什么意思 @3
```

**关键特性：只读取剪贴板，绝不写入。不影响你任何其他软件的复制粘贴。**

### 方式二：手动拖放

直接把图片拖进 `~/.kimi-cli/clips/inbox/`，一样自动分配编号、弹出气泡。

---

## 托盘菜单

右键托盘图标：

| 菜单项 | 功能 |
|---|---|
| Recent tags | 最近 5 张图的 `@N` 列表（点击复制编号） |
| Open clips folder | 打开截图保存目录 |
| View latest list | 打开 `latest.md`，查看全部编号 |
| Cleanup old clips | 手动清理 7 天前的旧截图 |
| Exit | 退出程序 |

左键单击托盘图标：直接打开 `latest.md` 查看全部编号。

---

## 编号规则

- **`@1`, `@2`, `@3`... 全局递增**，基于 `manifest.jsonl` 历史总条数，重启不重置
- **同一张图不会重复分配**，剪贴板去重基于 MD5
- **自动清理**：最多保留 50 张，超过或 7 天未访问自动删除

---

## 数据目录

```
C:\Users\<用户名>\.kimi-cli\clips\
├── inbox\                        # 拖放图片到这里也会被处理
├── 20260502_094812_345.png      # 自动保存的截图
├── manifest.jsonl               # 编号、文件名、时间的持久记录
├── latest.md                    # 最近 30 张索引（人可读）
└── daemon.log                   # 运行日志
```

---

## 常见问题

**Q: 必须手动把截图放进 inbox 吗？**
A: 不需要。剪贴板桥接会自动处理系统截图、微信截图、QQ 截图等。inbox 是留给手动拖放用的。

**Q: 连续截了 5 张图，怎么引用第 2 张？**
A: 左键单击托盘图标打开 `latest.md`，或右键菜单看 Recent tags。

**Q: 编号会重复或跳号吗？**
A: 不会。编号基于持久化的 `manifest.jsonl` 严格递增，除非手动删除该文件。

**Q: 会影响我正常使用复制粘贴吗？**
A: 完全不会。程序**只读取**剪贴板里的图片并保存到本地，**从不向剪贴板写入任何内容**。复制文字、复制文件等一切行为都不受影响。

**Q: 怎么彻底关闭？**
A: 右键托盘图标 → Exit。异常残留时在任务管理器结束 `KimiClipMon.exe`。

---

## License

MIT License — 详见 [LICENSE](LICENSE) 文件。
