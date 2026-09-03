"""
并发批处理调度引擎单元测试
测试多任务状态流转、并发限流、异常隔离与批量数据结构
"""

import unittest
from unittest.mock import patch, MagicMock
from src.schemas import (
    BatchTranscriptionRequest,
    BatchTranscriptionResponse,
    BatchItemProgress,
    TranscriptionResponse
)
from src.core.batch_engine import BatchTranscriptionEngine


class TestBatchEngine(unittest.TestCase):
    def test_batch_schemas(self):
        """测试批量 Schema 结构定义与校验"""
        req = BatchTranscriptionRequest(
            urls=["https://v.douyin.com/abc1234/", "https://bilibili.com/video/BV1xx411c7mD"],
            output_format="timestamped",
            max_workers=3
        )
        self.assertEqual(len(req.urls), 2)
        self.assertEqual(req.output_format, "timestamped")
        self.assertEqual(req.max_workers, 3)

        progress = BatchItemProgress(
            task_id="task_1_1001",
            url="https://test.com",
            status="downloading",
            message="正在下载"
        )
        self.assertEqual(progress.status, "downloading")

        resp = BatchTranscriptionResponse(
            status="partial_success",
            total_count=2,
            success_count=1,
            failed_count=1,
            results=[progress],
            elapsed_seconds=1.5
        )
        self.assertEqual(resp.total_count, 2)
        self.assertEqual(resp.success_count, 1)

    @patch("src.core.batch_engine.MediaExtractor.extract_media")
    @patch("src.core.batch_engine.VideoCleaner.clean_video")
    @patch("src.core.batch_engine.pipeline_engine._get_model")
    def test_batch_execution_mocked(self, mock_get_model, mock_clean_video, mock_extract_media):
        """测试批量并发执行流程与部分成功/失败隔离"""
        # 模拟下载
        def side_effect_extract(url, out_dir):
            if "fail" in url:
                raise RuntimeError("模拟下载超时或网络错误")
            return "/tmp/fake.wav", "/tmp/fake.mp4", {"title": f"标题_{url}", "duration": 10.0}

        mock_extract_media.side_effect = side_effect_extract

        # 模拟画质增强
        mock_clean_video.return_value = ("/tmp/fake_enhanced.mp4", True, True)

        # 模拟 Whisper 模型
        fake_segment = MagicMock()
        fake_segment.start = 0.0
        fake_segment.end = 2.0
        fake_segment.text = "测试文字"
        fake_info = MagicMock()
        fake_info.language = "zh"

        fake_model = MagicMock()
        fake_model.transcribe.return_value = ([fake_segment], fake_info)
        mock_get_model.return_value = fake_model

        engine = BatchTranscriptionEngine()
        test_urls = [
            "https://test.com/video1",
            "https://test.com/fail_video",
            "https://test.com/video2"
        ]

        progress_events = []
        def callback(task):
            progress_events.append((task.task_id, task.status))

        res = engine.execute_batch(
            urls=test_urls,
            output_format="paragraph",
            max_workers=2,
            progress_callback=callback
        )

        self.assertEqual(res.total_count, 3)
        self.assertEqual(res.success_count, 2)
        self.assertEqual(res.failed_count, 1)
        self.assertEqual(res.status, "partial_success")

        # 验证失败的任务被正确隔离并记录了错误
        failed_tasks = [t for t in res.results if t.status == "failed"]
        self.assertEqual(len(failed_tasks), 1)
        self.assertIn("网络错误", failed_tasks[0].error)

        # 验证成功的任务生成了有效结果
        success_tasks = [t for t in res.results if t.status == "completed"]
        self.assertEqual(len(success_tasks), 2)
        self.assertEqual(success_tasks[0].result.language, "zh")
        self.assertIn("测试文字", success_tasks[0].result.text)


if __name__ == "__main__":
    unittest.main()
