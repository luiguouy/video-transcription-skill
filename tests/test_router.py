"""
平台分类与认证策略路由器单元测试
"""

import unittest
from src.core.router import PlatformClassifier, AuthRequirement


class TestPlatformRouter(unittest.TestCase):
    def test_domain_classification(self):
        # 1. 免登录需新鲜签名平台 (Guest-Fresh)
        douyin_url = "https://v.douyin.com/rY0ksWQ0K1Q/"
        self.assertEqual(PlatformClassifier.classify_url(douyin_url), AuthRequirement.GUEST_FRESH)

        tiktok_url = "https://www.tiktok.com/@user/video/123456"
        self.assertEqual(PlatformClassifier.classify_url(tiktok_url), AuthRequirement.GUEST_FRESH)

        # 2. 强登录平台 (Account-Login)
        yt_url1 = "https://youtu.be/IDy2SxjMOFM"
        yt_url2 = "https://www.youtube.com/watch?v=abc"
        self.assertEqual(PlatformClassifier.classify_url(yt_url1), AuthRequirement.ACCOUNT_LOGIN)
        self.assertEqual(PlatformClassifier.classify_url(yt_url2), AuthRequirement.ACCOUNT_LOGIN)

        # 3. 开放平台 (Anonymous)
        bilibili_url = "https://www.bilibili.com/video/BV1pktD69Eh3"
        self.assertEqual(PlatformClassifier.classify_url(bilibili_url), AuthRequirement.ANONYMOUS)

    def test_error_diagnosis(self):
        # 识别抖音式访客签名错误
        err1 = "ERROR: [Douyin] Fresh cookies (not necessarily logged in) are needed"
        self.assertEqual(PlatformClassifier.diagnose_error(err1), AuthRequirement.GUEST_FRESH)

        # 识别 YouTube 强登录错误
        err2 = "ERROR: [youtube] Sign in to confirm you’re not a bot."
        self.assertEqual(PlatformClassifier.diagnose_error(err2), AuthRequirement.ACCOUNT_LOGIN)

        # 未知错误
        err3 = "Connection reset by peer"
        self.assertIsNone(PlatformClassifier.diagnose_error(err3))


if __name__ == "__main__":
    unittest.main()
