---
name: video-transcription
description: 视频解析、提取音频与本地语音转文字技能。当用户提供网络视频链接（支持抖音App复制的混杂文案、B站、YouTube、X、TikTok等）并希望获取文字稿、视频内容总结、提取音频、字幕切片或时间戳转写时激活此技能。纯本地 16kHz WAV 转码与 faster-whisper 高精度推理，零第三方云端 API 依赖。
---

# 视频解析与语音转文字 Skill (Video Transcription)

本 Skill 用于对网络视频链接进行多平台无感解析、提取音频流并进行高精度本地语音转写。

- **核心运行环境**：`D:\Antigravity_Workspaces\videoload_tran\venv`
- **CLI 调度入口**：`D:\Antigravity_Workspaces\videoload_tran\cli.py`
- **MCP 服务入口**：`D:\Antigravity_Workspaces\videoload_tran\src\server.py`

---

## 🎯 Agent 执行标准操作规程 (SOP)

当用户输入视频链接并需要转录/提取文字时，Agent 执行以下步骤：

### 步骤 1：直接调用 CLI 工具执行转录

在终端中执行以下命令（注意：必须使用该项目专属的 Python 虚拟环境解释器）：

#### 场景 A：获取连贯的段落正文（适合做内容总结、提取文案）
```bash
"D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe" "D:\Antigravity_Workspaces\videoload_tran\cli.py" "<视频链接或分享文本>" --format paragraph
```

#### 场景 B：获取带精确时间戳的字幕切片（适合按时间线回溯、截取精彩片段）
```bash
"D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe" "D:\Antigravity_Workspaces\videoload_tran\cli.py" "<视频链接或分享文本>" --format timestamped
```

#### 场景 C：保存到本地文件并获取 JSON 结构化数据
```bash
"D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe" "D:\Antigravity_Workspaces\videoload_tran\cli.py" "<视频链接或分享文本>" --json --output "output.json"
```

---

## 💡 特性与自动处理优势

1. **抖音分享文案免预处理**：直接传入抖音 App 点击“分享/复制链接”产生的整段文字即可，底层 `cleaner.py` 会自动提取其中的 URL 并跟随重定向。
2. **零显存浪费与并发保护**：模型推理为懒加载单例，内置线程锁防止多任务显存溢出 (OOM)。
3. **彻底抑制 Whisper 幻觉**：已内置配置 `condition_on_previous_text=False` 和 VAD 静音切除，杜绝纯音乐或静音时的“复读机”问题。
4. **长视频时间戳自适应**：支持超过 1 小时的视频，输出格式自动规范为 `[01:05:23.00 -> 01:05:28.50]`。
