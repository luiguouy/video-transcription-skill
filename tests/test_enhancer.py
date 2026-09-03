"""
画质增强与视频净化滤镜链构建单元测试
验证：
1. 仅去水印时的滤镜生成（单框与时间线分段多框）
2. 开启画质增强时的黄金拓扑顺序：
   format(10-bit) -> delogo -> atadenoise -> eq -> scale(lanczos+bt709) -> deband -> unsharp -> format(8-bit)
3. 参数关闭时的空列表返回
"""

import unittest
from src.core.watermark import VideoCleaner


class TestVideoEnhancer(unittest.TestCase):
    def test_build_filter_chain_none(self):
        filters = VideoCleaner.build_filter_chain(
            watermark_box=None,
            remove_subtitles=False,
            enhance_quality=False
        )
        self.assertEqual(filters, [])

    def test_build_filter_chain_watermark_only(self):
        filters = VideoCleaner.build_filter_chain(
            watermark_box=(10, 20, 100, 30),
            remove_subtitles=False,
            enhance_quality=False
        )
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0], "delogo=x=10:y=20:w=100:h=30:show=0")

    def test_build_filter_chain_timeline_watermark(self):
        timeline_boxes = [
            {'box': (580, 10, 300, 50), 't_start': 0.0, 't_end': 91.5},
            {'box': (560, 70, 320, 50), 't_start': 91.5, 't_end': 210.0}
        ]
        filters = VideoCleaner.build_filter_chain(
            watermark_box=timeline_boxes,
            remove_subtitles=False,
            enhance_quality=False
        )
        self.assertEqual(len(filters), 2)
        self.assertIn("delogo=x=580:y=10:w=300:h=50:enable='between(t,0.0,91.5)':show=0", filters[0])
        self.assertIn("delogo=x=560:y=70:w=320:h=50:enable='between(t,91.5,210.0)':show=0", filters[1])

    def test_build_filter_chain_enhance_full_order(self):
        filters = VideoCleaner.build_filter_chain(
            watermark_box=(15, 25, 120, 40),
            remove_subtitles=False,
            enhance_quality=True
        )

        # 预期包含 8 道工序（含末端 yuv420p 兼容性抖动输出）
        self.assertEqual(len(filters), 8)

        # 验证黄金顺序：
        # 1. 10-bit 管道
        self.assertTrue(filters[0].startswith("format=yuv420p10le"))
        # 2. delogo 在原始像素上消除
        self.assertTrue(filters[1].startswith("delogo=x=15:y=25:w=120:h=40"))
        # 3. atadenoise 动态降噪
        self.assertTrue(filters[2].startswith("atadenoise="))
        # 4. eq 调色
        self.assertTrue(filters[3].startswith("eq="))
        # 5. scale 自适应 + lanczos + bt709
        self.assertIn("flags=lanczos", filters[4])
        self.assertIn("out_color_matrix=bt709", filters[4])
        # 6. deband 去色带
        self.assertTrue(filters[5].startswith("deband"))
        # 7. unsharp 亮度微锐化
        self.assertTrue(filters[6].startswith("unsharp="))
        # 8. format=yuv420p 末端全设备兼容输出
        self.assertEqual(filters[7], "format=yuv420p")


if __name__ == "__main__":
    unittest.main()
