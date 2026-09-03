"""
文本清洗器与格式化单元测试
验证：
1. 抖音杂质分享文案 URL 提取
2. 中文字符空格消除与标点规范化
3. 长视频小时级时间戳分块
"""

import unittest
from types import SimpleNamespace
from src.core.cleaner import TextCleaner


class TestTextCleaner(unittest.TestCase):
    def test_extract_url_with_douyin_junk_text(self):
        # 模拟抖音 App 复杂复制文案
        raw = "7.28 03/12 S@s.xy cLg:/ 惊呆了！ https://v.douyin.com/ieABC/ 复制此链接，打开Douyin搜索"
        url = TextCleaner.extract_url(raw)
        self.assertTrue(url.startswith("http"))
        self.assertIn("douyin", url)

    def test_to_fluent_paragraph(self):
        # 模拟 Whisper 识别出的碎片和汉字间多余空格
        segments = [
            SimpleNamespace(text=" 这 是   一段 测试 文本,"),
            SimpleNamespace(text="包含 标点 规范化 ?"),
            SimpleNamespace(text="以及句子结尾")
        ]
        res = TextCleaner.to_fluent_paragraph(segments)
        # 汉字之间不应该有空格
        self.assertNotIn("这 是", res)
        self.assertIn("这是一段测试文本", res)
        # 英文标点替换为全角标点
        self.assertIn("，", res)
        self.assertIn("？", res)
        # 句尾补全句号
        self.assertTrue(res.endswith("。"))

    def test_to_timestamped_lines_normal_and_hour(self):
        # 模拟分钟级与小时级视频
        segments = [
            SimpleNamespace(start=12.5, end=18.3, text="第一句话"),
            SimpleNamespace(start=3665.2, end=3670.8, text="一小时后的内容")
        ]
        res = TextCleaner.to_timestamped_lines(segments)
        lines = res.split("\n")
        self.assertEqual(len(lines), 2)
        # 包含小时格式：01:01:05.20
        self.assertIn("01:01:05.20", lines[1])
        self.assertIn("一小时后的内容", lines[1])


if __name__ == "__main__":
    unittest.main()
