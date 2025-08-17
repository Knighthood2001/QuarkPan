"""
认证模块
"""

from .login import QuarkAuth, get_auth_cookies

try:
    from .qr_login import QRCodeLogin, qr_login
    __all__ = ['QuarkAuth', 'get_auth_cookies', 'QRCodeLogin', 'qr_login']
except ImportError:
    # 如果二维码相关依赖未安装，只导出基础功能
    __all__ = ['QuarkAuth', 'get_auth_cookies']
