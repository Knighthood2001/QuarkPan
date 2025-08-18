"""
夸克网盘登录模块
基于Playwright实现自动化登录和Cookie管理
"""

import os
import json
import time
from typing import Dict, List, Optional, Union
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("请安装playwright: pip install playwright")

from ..config import get_config_dir
from ..exceptions import AuthenticationError, ConfigError
from ..utils.logger import get_logger


class QuarkAuth:
    """夸克网盘认证管理器"""

    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """
        初始化认证管理器

        Args:
            headless: 是否无头模式运行浏览器
            slow_mo: 浏览器操作延迟(毫秒)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.config_dir = get_config_dir()
        self.cookies_file = self.config_dir / "cookies.json"
        self.browser_data_dir = self.config_dir / "browser_data"
        self.logger = get_logger(__name__)
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def _save_cookies(self, cookies: List[Dict]) -> None:
        """保存cookies到本地文件"""
        try:
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cookies': cookies,
                    'timestamp': int(time.time()),
                    'expires_at': self._get_cookies_expire_time(cookies)
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ConfigError(f"保存cookies失败: {e}")
    
    def _load_cookies(self) -> Optional[Dict]:
        """从本地文件加载cookies"""
        try:
            if not self.cookies_file.exists():
                return None

            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查cookies是否过期
            if self._is_cookies_expired(data):
                return None

            return data
        except Exception:
            return None
    
    def _get_cookies_expire_time(self, cookies: List[Dict]) -> Optional[int]:
        """获取cookies的过期时间"""
        min_expire = None
        for cookie in cookies:
            # 检查所有cookie，不只是quark域名的
            if 'expires' in cookie and cookie['expires'] > 0:
                expire_time = cookie['expires']
                if min_expire is None or expire_time < min_expire:
                    min_expire = expire_time

        # 如果没有找到有效的过期时间，返回一个合理的默认值（7天后）
        if min_expire is None:
            import time
            min_expire = int(time.time()) + (7 * 24 * 3600)

        return min_expire
    
    def _is_cookies_expired(self, cookie_data: Dict) -> bool:
        """检查cookies是否过期"""
        import time
        current_time = int(time.time())

        # 如果过期时间无效（None、-1等），使用时间戳检查
        expires_at = cookie_data.get('expires_at')
        if expires_at is None or expires_at <= 0:
            # 如果没有过期时间信息，检查是否超过7天
            timestamp = cookie_data.get('timestamp', 0)
            age_seconds = current_time - timestamp
            return age_seconds > (7 * 24 * 3600)

        return current_time > expires_at
    
    def _cookies_to_dict(self, cookies: List[Dict]) -> Dict[str, str]:
        """将cookies列表转换为字典格式"""
        result = {}
        for cookie in cookies:
            # 包含所有cookie，不只是quark域名的
            result[cookie['name']] = cookie['value']
        return result
    
    def _cookies_to_string(self, cookies: List[Dict]) -> str:
        """将cookies列表转换为字符串格式"""
        cookie_dict = self._cookies_to_dict(cookies)
        return '; '.join([f"{key}={value}" for key, value in cookie_dict.items()])
    
    def login(self, force_relogin: bool = False, use_qr: bool = True) -> str:
        """
        执行登录流程

        Args:
            force_relogin: 是否强制重新登录
            use_qr: 是否使用二维码登录

        Returns:
            Cookie字符串

        Raises:
            AuthenticationError: 登录失败
        """
        # 如果不是强制重新登录，先尝试使用已保存的cookies
        if not force_relogin:
            saved_cookies = self._load_cookies()
            if saved_cookies:
                return self._cookies_to_string(saved_cookies['cookies'])

        # 优先使用二维码登录
        if use_qr:
            try:
                from .qr_login import qr_login
                cookies = qr_login(headless=True)

                # 解析cookies字符串为列表格式
                cookie_list = self._parse_cookie_string(cookies)

                # 保存cookies
                self._save_cookies(cookie_list)
                return cookies

            except Exception:
                pass

        # 回退到手动登录
        return self._manual_login()

    def _parse_cookie_string(self, cookie_string: str) -> List[Dict]:
        """将cookie字符串解析为列表格式"""
        cookies = []
        for pair in cookie_string.split('; '):
            if '=' in pair:
                name, value = pair.split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.quark.cn',
                    'path': '/'
                })
        return cookies

    def _manual_login(self) -> str:
        """手动登录模式"""
        self.logger.info("启动浏览器进行手动登录")

        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.firefox.launch_persistent_context(
                    str(self.browser_data_dir),
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=['--start-maximized'] if not self.headless else [],
                    no_viewport=not self.headless
                )

                page = browser.pages[0] if browser.pages else browser.new_page()

                # 访问夸克网盘
                self.logger.info("正在打开夸克网盘")
                page.goto('https://pan.quark.cn/')

                # 等待用户登录
                if not self.headless:
                    input("\n请在浏览器中完成登录，登录成功后回到此处按 Enter 键继续...")
                else:
                    # 无头模式下需要自动检测登录状态
                    self._wait_for_login(page)

                # 获取cookies
                cookies = page.context.cookies()

                # 验证登录是否成功
                if not self._validate_cookies(cookies):
                    raise AuthenticationError("登录验证失败，请重试")

                # 保存cookies
                self._save_cookies(cookies)

                self.logger.info("登录成功")
                return self._cookies_to_string(cookies)

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"登录过程中发生错误: {e}")
    
    def _wait_for_login(self, page: Page, timeout: int = 300000) -> None:
        """等待用户完成登录（无头模式）"""
        # 这里可以实现自动检测登录状态的逻辑
        # 比如检查特定元素的出现、URL变化等
        pass
    
    def _validate_cookies(self, cookies: List[Dict]) -> bool:
        """验证cookies是否有效"""
        # 检查是否包含夸克相关的cookies
        quark_cookies = [c for c in cookies if 'quark' in c.get('domain', '')]
        return len(quark_cookies) > 0
    
    def get_cookies(self, force_relogin: bool = False) -> str:
        """
        获取有效的cookies字符串

        Args:
            force_relogin: 是否强制重新登录

        Returns:
            Cookie字符串
        """
        # 如果不强制重新登录，先尝试返回已保存的cookies
        if not force_relogin:
            saved_cookies = self._load_cookies()
            if saved_cookies:
                cookies = saved_cookies['cookies']
                cookie_string = self._cookies_to_string(cookies)

                # 简单验证：检查是否有必要的cookie
                required_cookies = ['__pus', '__puus']
                has_required = all(required in cookie_string for required in required_cookies)

                if has_required:
                    self.logger.debug("使用已保存的有效Cookie")
                    return cookie_string
                else:
                    self.logger.warning("已保存的Cookie缺少必要字段，需要重新登录")

        # 如果没有有效的cookies或强制重新登录，则执行登录
        return self.login(force_relogin)
    
    def logout(self) -> None:
        """登出并清除本地cookies"""
        try:
            if self.cookies_file.exists():
                self.cookies_file.unlink()
            self.logger.info("已清除登录信息")
        except Exception as e:
            self.logger.error(f"清除登录信息时出错: {e}")
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        saved_cookies = self._load_cookies()
        if saved_cookies is None:
            return False

        # 验证cookie是否有效
        try:
            cookies = saved_cookies['cookies']
            if not cookies:
                return False

            # 简单验证：检查是否有必要的cookie字段
            cookie_string = self._cookies_to_string(cookies)
            required_cookies = ['__pus', '__puus']  # 夸克网盘的关键cookie

            for required in required_cookies:
                if required not in cookie_string:
                    return False

            return True

        except Exception:
            return False


# 便捷函数
def get_auth_cookies(headless: bool = True, force_relogin: bool = False) -> str:
    """获取认证cookies的便捷函数"""
    auth = QuarkAuth(headless=headless)
    return auth.get_cookies(force_relogin=force_relogin)
