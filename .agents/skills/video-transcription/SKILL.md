---
name: video-transcription
description: 视频解析、提取音频、画质增强修复与本地语音转文字技能（支持多任务高并发批处理）。当用户提供单个或多个网络视频链接（支持抖音App复制的混杂文案、B站、YouTube、X、TikTok等）并希望获取文字稿、视频总结、提取音频、超清画质修复增强、字幕切片或批量转写时激活此技能。纯本地 16kHz WAV 转码、faster-whisper 高精度推理、FFmpeg 10-bit 黄金画质增强与分阶段算力信号量流水线，零第三方云端 API 依赖。
---

# 视频解析、语音转文字与画质增强 Skill (Video Transcription & Enhancement)

本 Skill 用于对网络视频链接进行多平台无感解析、提取高保真音频流、进行高精度本地语音转写，并按需执行工业级 10-bit 超清画质修复。已原生升级为**多任务分阶段并发模式**，兼顾高吞吐与硬件安全。

- **核心运行环境**：`D:\Antigravity_Workspaces\videoload_tran\venv`
- **CLI 调度入口**：`D:\Antigravity_Workspaces\videoload_tran\cli.py`
- **MCP 服务入口**：`D:\Antigravity_Workspaces\videoload_tran\src\server.py`

---

## 🎯 Agent 执行标准操作规程 (SOP)

当用户输入视频链接并需要转录/提取文字/画质增强时，Agent 执行以下步骤：

### 步骤 1：直接调用 CLI 工具执行任务

在终端中执行以下命令（注意：必须使用该项目专属的 Python 虚拟环境解释器）：

#### 场景 A：获取连贯的段落正文（适合单个视频总结、提取文案）
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

#### 场景 D：开启 10-bit 超清画质增强与修复（适合低清视频、去瑕疵、色彩与细节提升）
当用户提到“提高画质”、“画质增强”、“清晰度修复”、“高清导出”等需求时，添加 `--enhance` 参数：
```bash
"D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe" "D:\Antigravity_Workspaces\videoload_tran\cli.py" "<视频链接或分享文本>" --enhance --format paragraph
```

#### 场景 E：【并发批处理】多视频并行转录（直接输入多个链接或分享文案）
当用户一次性提供多个视频链接或多条分享文案时，直接传入多个参数，底层自动启动多任务并发看板：
```bash
"D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe" "D:\Antigravity_Workspaces\videoload_tran\cli.py" "<链接1>" "<链接2>" "<链接3>" --concurrency 3 --output-dir "batch_results"
```

#### 场景 F：【并发批处理】从链接文件批量导入并分类落盘
若用户提供了一个包含大量视频链接的文本文件（每行一个链接）：
```bash
"D:\Antigravity_Workspaces\videoload_tran\venv\Scripts\python.exe" "D:\Antigravity_Workspaces\videoload_tran\cli.py" --file "urls.txt" --concurrency 4 --output-dir "batch_results"
```

---

## 💡 特性与并发流水线优势

1. **分阶段算力信号量 (Staged Semaphores)**：
   - **下载阶段 (I/O密集)**：网络高并发并行抓取；
   - **增强阶段 (CPU密集)**：严格控制 FFmpeg 10-bit 超清增强并发（默认 1~2），杜绝系统假死；
   - **推理阶段 (显存/内存密集)**：Whisper 模型单例推理互斥排队，杜绝 CUDA OOM；
   - 形成流水线交叠（视频 1 推理时，视频 2 渲染，视频 3/4 并发下载），吞吐量成倍飙升。
2. **任务隔离与容错**：单个视频抓取或解析异常自动记录失败原因，不影响整批队列其他视频。
3. **Rich 动态并发监控面板**：实时刷新各任务当前状态（排队中、下载中、滤镜处理中、Whisper 推理中、已完成）。
4. **抖音分享文案免预处理**：直接传入抖音 App 点击“分享/复制链接”产生的整段文字即可，底层 `cleaner.py` 会自动提取其中的 URL 并跟随重定向。
5. **彻底抑制 Whisper 幻觉**：已内置配置 `condition_on_previous_text=False` 和 VAD 静音切除，杜绝纯音乐或静音时的“复读机”问题。
6. **默认持久化保存模式**：音视频文件默认保存于 `downloads/` 目录中，保留完整原始高保真 16kHz WAV 音频与 MP4 视频，永不自动删除，由用户掌控清理。
7. **工业级高保真画质增强管线**：10-bit 内部计算管道防色阶断层，BT.709 色彩校准与 Lanczos 放大，末端输出兼容全设备秒开播放的标准 8-bit YUV420P。
8. **Edge & Chrome 双浏览器全自动智能兼容**：系统默认配置 `COOKIES_FROM_BROWSER=auto`，全自动探测当前系统已安装的 Edge 与 Chrome 浏览器；支持多浏览器轮询与独占锁平滑回退，无论用户主力浏览器是 Edge 还是 Chrome 均能免手动切换，亦可回退到 `cookies.txt`，保证高风控视频抓取成功率。
9. **TikTok 受限视频自动回退与系统代理自动嗅探**：针对 TikTok 观众管理/强制登录的敏感限制视频，底层自动无感回退至 TikWM 高清直链解析通道；并自动嗅探 Windows 系统网络代理，零手动配置海外直连与高可靠抓取。
