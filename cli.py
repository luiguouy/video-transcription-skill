"""
命令行 CLI 入口
支持单视频转写与多视频并发批处理 (基于 faster-whisper + yt-dlp + FFmpeg)
"""

import sys
import os
import argparse
import json
import time
from typing import List

from rich.console import Console
from rich.table import Table
from rich.live import Live

from src.config import settings
from src.core.cleaner import TextCleaner
from src.core.transcriber import pipeline_engine
from src.core.batch_engine import batch_engine, BatchTranscriptionEngine
from src.schemas import BatchItemProgress, BatchTranscriptionResponse


console = Console()
stderr_console = Console(stderr=True)


def render_progress_table(tasks: List[BatchItemProgress], overall_title: str = "多视频并发处理看板") -> Table:
    """构建 Rich 动态进度表格"""
    table = Table(title=overall_title, show_lines=True)
    table.add_column("序号", justify="center", style="cyan", no_wrap=True)
    table.add_column("任务ID", justify="center", style="dim", no_wrap=True)
    table.add_column("视频标题", style="bold", max_width=32, overflow="ellipsis")
    table.add_column("状态", justify="center", no_wrap=True)
    table.add_column("阶段详情 / 结果说明", style="dim", max_width=45, overflow="ellipsis")

    status_styles = {
        "pending": "[yellow]⏳ 排队中[/yellow]",
        "downloading": "[blue]📥 下载与提取中[/blue]",
        "enhancing": "[magenta]✨ 超清滤镜处理中[/magenta]",
        "transcribing": "[cyan]🎙️ Whisper推理中[/cyan]",
        "completed": "[green]✅ 已完成[/green]",
        "failed": "[red]❌ 失败[/red]",
    }

    for idx, t in enumerate(tasks, 1):
        status_text = status_styles.get(t.status, t.status)
        detail_text = t.error if t.status == "failed" else (t.message or "")
        title_text = t.title or t.url[:30]
        table.add_row(str(idx), t.task_id, title_text, status_text, detail_text)

    return table


def run_single(args, url: str):
    """单视频处理模式（与原有行为完全兼容）"""
    res = pipeline_engine.execute(
        raw_url=url,
        output_format=args.format,
        language=args.language,
        auto_remove_watermark=args.auto_remove_watermark,
        remove_subtitles=args.remove_subtitles,
        enhance_quality=args.enhance
    )

    if res.status == "error":
        stderr_console.print(f"[bold red][错误][/bold red] {res.error_message}")
        sys.exit(1)

    if args.json:
        output_data = res.model_dump()
        output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
    else:
        media_info_list = []
        if res.video_path:
            tags = []
            if res.watermark_detected:
                tags.append("已自动消除创作者水印")
            if res.quality_enhanced:
                tags.append("已执行 10-bit 超清画质增强")
            wm_tag = f" ({' | '.join(tags)})" if tags else ""
            media_info_list.append(f"【媒体保存】完整视频: {res.video_path}{wm_tag}")
        if res.audio_path:
            media_info_list.append(f"【媒体保存】提取音频: {res.audio_path}")
        media_info = ("\n".join(media_info_list) + "\n") if media_info_list else ""
        header = (
            f"【视频信息】标题: {res.title} | 时长: {res.duration}秒 | 识别语种: {res.language}\n"
            f"{media_info}"
            f"【输出模式】{res.format}\n"
            "----------------------------------------\n"
        )
        output_str = header + res.text

    if args.output:
        out_path = os.path.abspath(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output_str)
        console.print(f"[bold green][成功][/bold green] 结果已保存至: {out_path}")
    else:
        print(output_str)


def run_batch(args, urls: List[str]):
    """多视频并发批处理模式"""
    # 动态调整信号量与并发配置
    if args.downloads_concurrency:
        batch_engine._io_semaphore = type(batch_engine._io_semaphore)(value=args.downloads_concurrency)
    if args.renders_concurrency:
        batch_engine._render_semaphore = type(batch_engine._render_semaphore)(value=args.renders_concurrency)
    if args.transcribes_concurrency:
        batch_engine._transcribe_semaphore = type(batch_engine._transcribe_semaphore)(value=args.transcribes_concurrency)

    concurrency = args.concurrency or settings.MAX_CONCURRENT_TASKS
    console.print(
        f"[bold cyan]>>> 启动多视频并发批处理[/bold cyan] [dim](总任务数: {len(urls)}, 线程池并发: {concurrency}, "
        f"下载限额: {settings.MAX_CONCURRENT_DOWNLOADS}, 渲染限额: {settings.MAX_CONCURRENT_RENDERS}, "
        f"转录限额: {settings.MAX_CONCURRENT_TRANSCRIBES})[/dim]"
    )

    task_map = {}

    with Live(render_progress_table([]), refresh_per_second=4, console=console) as live:
        def on_progress(task: BatchItemProgress):
            task_map[task.task_id] = task
            # 保持原始任务列表顺序渲染表格
            sorted_tasks = list(task_map.values())
            live.update(render_progress_table(sorted_tasks, overall_title=f"并发处理看板 (已提交: {len(urls)})"))

        response: BatchTranscriptionResponse = batch_engine.execute_batch(
            urls=urls,
            output_format=args.format,
            language=args.language,
            auto_remove_watermark=args.auto_remove_watermark,
            remove_subtitles=args.remove_subtitles,
            enhance_quality=args.enhance,
            download_only=args.download_only,
            max_workers=concurrency,
            progress_callback=on_progress
        )

    # 批处理完成后的聚合输出与归档
    console.print(
        f"\n[bold green]>>> 批处理执行完毕！[/bold green] "
        f"总数: {response.total_count} | [green]成功: {response.success_count}[/green] | "
        f"[red]失败: {response.failed_count}[/red] | 总耗时: {response.elapsed_seconds}秒\n"
    )

    # 如果指定了归档目录 --output-dir，逐个保存文本和 JSON
    if args.output_dir:
        out_dir = os.path.abspath(args.output_dir)
        os.makedirs(out_dir, exist_ok=True)
        for item in response.results:
            if item.status == "completed" and item.result:
                safe_title = "".join(c for c in (item.title or item.task_id) if c.isalnum() or c in (" ", "_", "-")).strip()[:40]
                txt_path = os.path.join(out_dir, f"{safe_title}_{item.task_id}.txt")
                json_path = os.path.join(out_dir, f"{safe_title}_{item.task_id}.json")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(item.result.text)
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(item.result.model_dump(), ensure_ascii=False, indent=2))
        console.print(f"[bold green][归档][/bold green] 批处理结果已分类保存至目录: {out_dir}")

    # 如果指定了 --output 文件
    if args.output:
        out_path = os.path.abspath(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            if args.json:
                f.write(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))
            else:
                summary_lines = [
                    f"=== 批量转录汇总报告 ===",
                    f"总计任务: {response.total_count} | 成功: {response.success_count} | 失败: {response.failed_count} | 耗时: {response.elapsed_seconds}s\n"
                ]
                for idx, item in enumerate(response.results, 1):
                    summary_lines.append(f"【任务 {idx}】{item.title or item.url}")
                    summary_lines.append(f"状态: {item.status}")
                    if item.result:
                        summary_lines.append(f"时长: {item.result.duration}s | 语言: {item.result.language}")
                        if item.result.video_path:
                            summary_lines.append(f"视频路径: {item.result.video_path}")
                        if item.result.audio_path:
                            summary_lines.append(f"音频路径: {item.result.audio_path}")
                        summary_lines.append("识别文本:\n" + item.result.text)
                    elif item.error:
                        summary_lines.append(f"错误信息: {item.error}")
                    summary_lines.append("-" * 40 + "\n")
                f.write("\n".join(summary_lines))
        console.print(f"[bold green][成功][/bold green] 批量汇总报告已保存至: {out_path}")
    elif args.json:
        print(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="本地音视频解析与语音转文字 CLI 工具 (支持单任务与多视频并发批处理)"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="视频网页链接或分享文本（支持传入多个链接进行并发处理）"
    )
    parser.add_argument(
        "--file", "-i",
        default=None,
        help="从指定文本文件读取批量视频链接列表（每行一个链接或文本，支持 # 注释）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["paragraph", "timestamped"],
        default="paragraph",
        help="输出格式: paragraph (连贯规范段落) 或 timestamped (时间戳字幕切片)，默认 paragraph"
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        help="语言代码（如 'zh', 'en'），默认自动检测"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出结果文件路径（若为单视频则保存该视频结果；若为批量则保存汇总报告）"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="批量模式下的结果归档目录（将每个视频的文本与 JSON 分别落盘保存）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="是否以 JSON 格式输出完整元数据与切片结构"
    )
    parser.add_argument(
        "--no-del-watermark",
        action="store_false",
        dest="auto_remove_watermark",
        default=True,
        help="禁用创作者水印自动消除（默认开启全自动消除）"
    )
    parser.add_argument(
        "--remove-subtitles",
        action="store_true",
        default=False,
        help="消除视频底部硬字幕（默认关闭）"
    )
    parser.add_argument(
        "--enhance", "-e",
        action="store_true",
        default=False,
        help="开启 10-bit 超清画质增强管线（含动态降噪、BT.709校色、Lanczos超采与去色带锐化）"
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        default=False,
        help="仅执行视频抓取与音频提取，跳过滤镜增强与语音识别（适合纯视频下载与并发测试）"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=None,
        help=f"批处理最大线程并发数（默认 {settings.MAX_CONCURRENT_TASKS}）"
    )
    parser.add_argument(
        "--downloads-concurrency",
        type=int,
        default=None,
        help=f"下载阶段最大并发限额（默认 {settings.MAX_CONCURRENT_DOWNLOADS}）"
    )
    parser.add_argument(
        "--renders-concurrency",
        type=int,
        default=None,
        help=f"画质滤镜渲染阶段最大并发限额（默认 {settings.MAX_CONCURRENT_RENDERS}）"
    )
    parser.add_argument(
        "--transcribes-concurrency",
        type=int,
        default=None,
        help=f"Whisper 模型推理最大并发限额（默认 {settings.MAX_CONCURRENT_TRANSCRIBES}）"
    )

    args = parser.parse_args()

    # 汇总输入链接
    url_list = list(args.urls) if args.urls else []
    if args.file:
        file_path = os.path.abspath(args.file)
        if not os.path.exists(file_path):
            console.print(f"[bold red][错误][/bold red] 找不到指定的链接文件: {file_path}", file=sys.stderr)
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#"):
                    url_list.append(line_str)

    if not url_list:
        parser.print_help()
        console.print("\n[bold red][提示][/bold red] 请至少提供一个视频链接或通过 --file 指定包含链接的文件。", file=sys.stderr)
        sys.exit(1)

    # 判断是单视频模式还是批量并发模式
    if len(url_list) == 1 and not args.file and not args.output_dir:
        run_single(args, url_list[0])
    else:
        run_batch(args, url_list)


if __name__ == "__main__":
    main()
