"""
协议模型单元测试
验证入参与出参的 Pydantic 校验逻辑
"""

import unittest
from src.schemas import TranscriptionRequest, TranscriptionResponse, SegmentItem


class TestSchemas(unittest.TestCase):
    def test_request_schema(self):
        req = TranscriptionRequest(url="https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(req.output_format, "paragraph")
        self.assertIsNone(req.language)
        self.assertTrue(req.auto_remove_watermark)
        self.assertFalse(req.remove_subtitles)
        self.assertFalse(req.enhance_quality)

        req2 = TranscriptionRequest(
            url="https://youtube.com/watch?v=123",
            output_format="timestamped",
            language="zh",
            auto_remove_watermark=False,
            remove_subtitles=True,
            enhance_quality=True
        )
        self.assertEqual(req2.output_format, "timestamped")
        self.assertEqual(req2.language, "zh")
        self.assertFalse(req2.auto_remove_watermark)
        self.assertTrue(req2.remove_subtitles)
        self.assertTrue(req2.enhance_quality)

    def test_response_schema(self):
        resp = TranscriptionResponse(
            status="success",
            title="测试视频",
            duration=120.5,
            language="zh",
            format="paragraph",
            text="这是测试识别文本。",
            segments=[SegmentItem(start=0.0, end=2.0, text="这是测试")]
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(len(resp.segments), 1)
        self.assertIsNone(resp.audio_path)
        self.assertFalse(resp.watermark_detected)
        self.assertFalse(resp.quality_enhanced)
        resp.audio_path = "/path/to/audio.wav"
        resp.watermark_detected = True
        resp.quality_enhanced = True
        self.assertEqual(resp.audio_path, "/path/to/audio.wav")
        self.assertTrue(resp.watermark_detected)
        self.assertTrue(resp.quality_enhanced)


if __name__ == "__main__":
    unittest.main()
