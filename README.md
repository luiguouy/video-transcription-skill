# 视频解析与语音转文字 AI Agent 技能服务 (FastMCP 本地版)

本项目是专为本地 AI Agent（Claude Desktop、Cursor、Dify 等）打造的高性能媒体感知与转写 Skill。接收视频链接（抖音、B站、YouTube 等）后，自动提取音频流，并通过本地 `faster-whisper` 实现低延迟、高精度的语音转写。

## ✨ 核心特性

- **多平台链接无感支持**：自动剥离抖音剪贴板中的冗余分享文案，提取纯净 URL；支持各大主流视频网站。
- **纯本地运算，零 API 费用**：基于 `faster-whisper` (CTranslate2)，在普通显卡或纯 CPU 上均可流畅推理。
- **单例懒加载与并发安全**：服务启动时不占显存，首次调用按需载入；内置线程锁杜绝并发推理导致的显存溢出 (OOM)。
- **杜绝 Whisper 幻觉**：关闭上下文连续推测 (`condition_on_previous_text=False`) 并配合 VAD 静音切除，根治纯音乐/静音片段的“复读机”问题。
- **双模文本交付**：
  - **连贯段落模式 (`paragraph`)**：消除中文字符间空格，规范化标点符号，确保句末标点完整。
  - **时间戳字幕模式 (`timestamped`)**：智能自适应支持小时级/分钟级高精度时间分块。
- **上下文过载保护**：转写内容超长时（>8000 字符）自动落地本地文本，防止击穿宿主 Agent 的上下文窗口。
- **沙箱级无痕回收**：媒体文件在独立临时沙箱中处理，转录完成即刻彻底删除，零磁盘残留。

---

## 🛠️ 前置准备

### 1. 系统底层依赖：FFmpeg

必须确保系统环境变量 `PATH` 中可直接调用 `ffmpeg`：

- **Windows**:
  1. 下载 [FFmpeg Release Essentials](https://www.gyan.dev/ffmpeg/builds/)；
  2. 解压并将 `bin` 目录路径添加至系统环境变量 `Path` 中；
  3. 终端输入 `ffmpeg -version` 验证。
- **macOS**:
  ```bash
  brew install ffmpeg
  ```
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

---

## 🚀 安装与配置

### 1. 创建虚拟环境并安装依赖

```bash
# 进入项目目录
cd d:/Antigravity_Workspaces/videoload_tran

# 创建并激活虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
# source venv/bin/activate

# 安装生产依赖
pip install -r requirements.txt
```

### 2. 环境变量配置（可选）

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

可根据机器硬件修改：
```ini
WHISPER_MODEL_SIZE=base        # 推荐 base / small，显存充裕可选 large-v3
WHISPER_DEVICE=auto            # auto / cuda / cpu
WHISPER_COMPUTE_TYPE=default   # cuda 建议 float16，cpu 建议 int8
```

---

## 🔌 接入 AI Agent (以 MCP 为例)

### 1. Claude Desktop 配置

在 Claude Desktop 配置文件（Windows: `%APPDATA%\Claude\claude_desktop_config.json`）中添加：

```json
{
  "mcpServers": {
    "video-transcriber": {
      "command": "D:\\Antigravity_Workspaces\\videoload_tran\\venv\\Scripts\\python.exe",
      "args": ["D:\\Antigravity_Workspaces\\videoload_tran\\src\\server.py"]
    }
  }
}
```

### 2. Cursor 配置

在 Cursor 的 `Settings` -> `Features` -> `MCP` -> `Add new MCP server` 中填写：
- **Name**: `video-transcriber`
- **Type**: `command`
- **Command**: `D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe D:\Antigravity_Workspaces\videoload_tran\src\server.py`

---

## 🧪 模块单元自测

在项目根目录下执行测试验证核心清洗与逻辑组件：

```bash
python tests/test_cleaner.py
```
