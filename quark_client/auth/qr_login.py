"""
二维码登录模块
"""

import time
import base64
import asyncio
from typing import Optional, Tuple
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser
    import qrcode
    from PIL import Image
    import io
except ImportError as e:
    missing_pkg = str(e).split("'")[1]
    raise ImportError(f"请安装缺失的依赖: pip install {missing_pkg}")

from ..config import get_config_dir
from ..exceptions import AuthenticationError
from ..utils.qr_code import display_qr_code


class QRCodeLogin:
    """二维码登录管理器"""

    def __init__(self, headless: bool = True, timeout: int = 300):
        """
        初始化二维码登录

        Args:
            headless: 是否使用无头模式
            timeout: 登录超时时间（秒）
        """
        self.headless = headless
        self.timeout = timeout
        self.config_dir = get_config_dir()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_browser()

    async def start_browser(self):
        """启动浏览器"""
        playwright = await async_playwright().start()

        # 启动Firefox浏览器
        self.browser = await playwright.firefox.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )

        # 创建新页面
        self.page = await self.browser.new_page()

        # 设置用户代理
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    async def close_browser(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()

    async def extract_qr_code(self) -> Tuple[str, str]:
        """
        提取二维码

        Returns:
            (qr_data, qr_image_path) 二维码数据和图片路径
        """
        print("🌐 正在打开夸克网盘登录页面...")

        # 访问登录页面，增加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.page.goto(
                    'https://pan.quark.cn/',
                    wait_until='domcontentloaded',  # 改为更快的加载条件
                    timeout=15000  # 减少超时时间
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"⚠️ 页面加载失败，重试 {attempt + 1}/{max_retries}...")
                await asyncio.sleep(2)

        # 等待页面稳定
        await asyncio.sleep(3)

        # 等待页面完全加载
        await asyncio.sleep(3)

        # 查找并点击登录相关按钮
        login_selectors = [
            'text=登录',
            'text=立即登录',
            'text=扫码登录',
            '[class*="login"]',
            'button:has-text("登录")',
            'a:has-text("登录")'
        ]

        for selector in login_selectors:
            try:
                login_element = await self.page.wait_for_selector(selector, timeout=3000)
                if login_element:
                    await login_element.click()
                    print(f"✅ 已点击登录元素: {selector}")
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue

        # 等待二维码出现
        print("🔍 正在查找二维码...")
        await asyncio.sleep(3)

        # 更全面的二维码选择器
        qr_selectors = [
            # Canvas元素
            'canvas',
            'canvas[width]',
            'canvas[height]',

            # 图片元素
            'img[src*="qr"]',
            'img[src*="QR"]',
            'img[src*="qrcode"]',
            'img[alt*="二维码"]',
            'img[alt*="QR"]',

            # 类名选择器
            '.qr-code',
            '.qrcode',
            '.QRCode',
            '[class*="qr"]',
            '[class*="QR"]',
            '[class*="code"]',

            # ID选择器
            '#qrcode',
            '#qr-code',
            '#QRCode',

            # 数据属性
            '[data-qr]',
            '[data-qrcode]'
        ]

        qr_element = None
        found_selector = None

        for selector in qr_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    # 检查每个元素是否可见且有内容
                    for element in elements:
                        is_visible = await element.is_visible()
                        if is_visible:
                            # 检查元素尺寸
                            box = await element.bounding_box()
                            if box and box['width'] > 50 and box['height'] > 50:
                                qr_element = element
                                found_selector = selector
                                print(f"✅ 找到二维码元素: {selector} (尺寸: {box['width']}x{box['height']})")
                                break

                    if qr_element:
                        break

            except Exception as e:
                print(f"⚠️ 检查选择器 {selector} 时出错: {e}")
                continue

        if not qr_element:
            # 尝试截取整个页面来调试
            debug_path = self.config_dir / "debug_page.png"
            await self.page.screenshot(path=str(debug_path))
            print(f"🔍 已保存调试截图到: {debug_path}")

            # 获取页面HTML来分析
            html_content = await self.page.content()
            debug_html_path = self.config_dir / "debug_page.html"
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"🔍 已保存页面HTML到: {debug_html_path}")

            raise AuthenticationError("未找到二维码元素，请检查调试文件")

        # 截取二维码图片
        qr_image_path = self.config_dir / "qr_code.png"
        await qr_element.screenshot(path=str(qr_image_path))
        print(f"📸 二维码已保存到: {qr_image_path}")

        # 验证图片是否有效
        try:
            from PIL import Image
            img = Image.open(qr_image_path)
            width, height = img.size
            print(f"📏 二维码图片尺寸: {width}x{height}")

            if width < 50 or height < 50:
                print("⚠️ 二维码图片尺寸过小，可能提取失败")
        except Exception as e:
            print(f"⚠️ 验证二维码图片时出错: {e}")

        # 尝试获取二维码数据（如果是canvas）
        qr_data = ""
        try:
            tag_name = await qr_element.evaluate('el => el.tagName')
            if tag_name == 'CANVAS':
                # 从canvas获取数据URL
                qr_data = await qr_element.evaluate(
                    'canvas => canvas.toDataURL()'
                )
                print("✅ 已从Canvas获取二维码数据")
        except Exception as e:
            print(f"⚠️ 获取Canvas数据时出错: {e}")

        return qr_data, str(qr_image_path)

    def display_qr_code(self, qr_image_path: str):
        """
        显示二维码

        Args:
            qr_image_path: 二维码图片路径
        """
        display_qr_code(qr_image_path)

    async def wait_for_login(self) -> bool:
        """
        等待用户扫码登录

        Returns:
            是否登录成功
        """
        print("⏳ 等待扫码登录...")
        print("💡 请使用夸克APP扫描二维码...")
        start_time = time.time()
        check_count = 0

        while time.time() - start_time < self.timeout:
            try:
                check_count += 1
                elapsed = time.time() - start_time
                print(f"🔍 检查登录状态... ({check_count}) - 已等待 {elapsed:.0f}秒")

                # 检查page是否有效
                if not self.page:
                    print("❌ 页面对象无效")
                    return False

                # 获取当前URL
                current_url = self.page.url
                print(f"🔗 当前URL: {current_url}")

                # 更严格的登录检测逻辑
                if 'pan.quark.cn' in current_url:
                    # 首先检查是否还在登录相关页面
                    if '/login' in current_url or '/passport' in current_url or 'login' in current_url.lower():
                        print("🔍 仍在登录页面，继续等待...")
                        await asyncio.sleep(3)
                        continue

                    print("🔍 检测到可能的页面跳转，验证登录状态...")

                    # 等待页面稳定
                    await asyncio.sleep(5)

                    # 检查页面标题
                    try:
                        title = await self.page.title()
                        print(f"📄 页面标题: {title}")
                        if '登录' in title or 'login' in title.lower():
                            print("⚠️ 页面标题显示仍在登录页面")
                            await asyncio.sleep(3)
                            continue
                    except Exception:
                        pass

                    # 严格检查登录成功的标志
                    success_indicators = 0
                    success_selectors = [
                        ('text=我的文件', '我的文件菜单'),
                        ('text=个人中心', '个人中心菜单'),
                        ('text=退出登录', '退出登录按钮'),
                        ('[class*="avatar"]', '用户头像'),
                        ('text=回收站', '回收站菜单'),
                        ('.file-list', '文件列表'),
                        ('[data-testid="file-list"]', '文件列表容器')
                    ]

                    for selector, description in success_selectors:
                        try:
                            element = await self.page.wait_for_selector(selector, timeout=2000)
                            if element and await element.is_visible():
                                print(f"✅ 找到登录标志: {description}")
                                success_indicators += 1
                        except Exception:
                            continue

                    # 需要至少找到2个成功标志才认为登录成功
                    if success_indicators >= 2:
                        print(f"✅ 找到 {success_indicators} 个登录成功标志，确认登录成功！")
                        return True
                    else:
                        print(f"⚠️ 只找到 {success_indicators} 个登录标志，可能未完全登录，继续等待...")
                        await asyncio.sleep(3)
                        continue

                # 检查二维码状态
                try:
                    # 检查二维码是否过期
                    expired_selectors = [
                        'text=二维码已过期',
                        'text=刷新二维码',
                        'text=重新获取',
                        '.qr-expired',
                        '[class*="expired"]'
                    ]

                    for selector in expired_selectors:
                        expired_element = await self.page.query_selector(selector)
                        if expired_element:
                            print("⚠️ 二维码已过期")
                            return False

                    # 检查是否有扫码成功但未确认的状态
                    scanned_selectors = [
                        'text=扫码成功',
                        'text=请在手机上确认',
                        'text=确认登录',
                        '.qr-scanned'
                    ]

                    for selector in scanned_selectors:
                        scanned_element = await self.page.query_selector(selector)
                        if scanned_element:
                            print("📱 检测到扫码成功，请在手机上确认登录")
                            break

                except Exception as e:
                    print(f"⚠️ 检查二维码状态时出错: {e}")

                # 等待间隔
                await asyncio.sleep(3)

            except Exception as e:
                print(f"⚠️ 检查登录状态时出错: {e}")
                await asyncio.sleep(3)

        print("⏰ 登录超时")
        return False

    async def get_cookies(self) -> str:
        """
        获取登录后的Cookies

        Returns:
            Cookie字符串
        """
        if not self.page:
            raise AuthenticationError("浏览器页面未初始化")

        # 获取所有cookies
        cookies = await self.page.context.cookies()

        # 转换为字符串格式
        cookie_pairs = []
        for cookie in cookies:
            cookie_pairs.append(f"{cookie['name']}={cookie['value']}")

        cookie_string = "; ".join(cookie_pairs)

        # 验证关键Cookie是否存在
        required_cookies = ['__pus', '__puus']
        missing_cookies = []

        for required in required_cookies:
            if required not in cookie_string:
                missing_cookies.append(required)

        if missing_cookies:
            print(f"⚠️ 缺少关键Cookie: {missing_cookies}")
            print("🔍 这可能表示登录未完全成功，尝试等待更长时间...")

            # 等待更长时间让登录完成
            await asyncio.sleep(10)

            # 重新获取cookies
            cookies = await self.page.context.cookies()
            cookie_pairs = []
            for cookie in cookies:
                cookie_pairs.append(f"{cookie['name']}={cookie['value']}")

            cookie_string = "; ".join(cookie_pairs)

            # 再次验证
            still_missing = []
            for required in required_cookies:
                if required not in cookie_string:
                    still_missing.append(required)

            if still_missing:
                raise AuthenticationError(f"登录失败：缺少必要的Cookie {still_missing}")
            else:
                print("✅ 延迟后获取到完整Cookie")

        print(f"✅ Cookie验证通过，包含 {len(cookies)} 个cookie")
        return cookie_string

    async def login(self) -> str:
        """
        执行完整的二维码登录流程

        Returns:
            Cookie字符串
        """
        try:
            # 提取二维码
            qr_data, qr_image_path = await self.extract_qr_code()

            # 显示二维码
            self.display_qr_code(qr_image_path)

            # 等待登录
            if await self.wait_for_login():
                # 获取cookies
                cookies = await self.get_cookies()
                print("🍪 已获取登录凭证")
                return cookies
            else:
                raise AuthenticationError("登录失败或超时")

        except Exception as e:
            raise AuthenticationError(f"二维码登录失败: {e}")


# 同步包装函数
def qr_login(headless: bool = True, timeout: int = 300) -> str:
    """
    同步的二维码登录函数

    Args:
        headless: 是否使用无头模式
        timeout: 超时时间

    Returns:
        Cookie字符串
    """
    async def _login():
        async with QRCodeLogin(headless=headless, timeout=timeout) as qr:
            return await qr.login()

    return asyncio.run(_login())
