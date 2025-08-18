"""
夸克网盘客户端主类
"""

from typing import Optional, Dict, List, Any
from .core.api_client import QuarkAPIClient
from .services.file_service import FileService
from .services.share_service import ShareService
from .auth import QuarkAuth


class QuarkClient:
    """夸克网盘客户端主类"""
    
    def __init__(self, cookies: Optional[str] = None, auto_login: bool = True):
        """
        初始化夸克网盘客户端
        
        Args:
            cookies: Cookie字符串，如果为None则自动获取
            auto_login: 是否自动登录
        """
        # 初始化API客户端
        self.api_client = QuarkAPIClient(cookies=cookies, auto_login=auto_login)
        
        # 初始化服务
        self.files = FileService(self.api_client)
        self.shares = ShareService(self.api_client)
        
        # 保存认证信息
        self._auth = None
    
    @property
    def auth(self) -> QuarkAuth:
        """获取认证管理器"""
        if not self._auth:
            self._auth = QuarkAuth()
        return self._auth
    
    def login(self, force_relogin: bool = False, use_qr: bool = True) -> str:
        """
        执行登录

        Args:
            force_relogin: 是否强制重新登录
            use_qr: 是否使用二维码登录

        Returns:
            Cookie字符串
        """
        cookies = self.auth.login(force_relogin, use_qr)
        self.api_client.cookies = cookies
        return cookies
    
    def logout(self):
        """登出"""
        self.auth.logout()
        self.api_client.cookies = None
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.auth.is_logged_in()
    
    # 文件管理快捷方法
    def list_files(self, folder_id: str = "0", **kwargs) -> Dict[str, Any]:
        """获取文件列表"""
        return self.files.list_files(folder_id, **kwargs)
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """获取文件信息"""
        return self.files.get_file_info(file_id)

    def search_files(self, keyword: str, **kwargs) -> Dict[str, Any]:
        """搜索文件"""
        return self.files.search_files(keyword, **kwargs)

    def get_download_url(self, file_id: str) -> str:
        """获取下载链接"""
        return self.files.get_download_url(file_id)

    def get_download_urls(self, file_ids: List[str]) -> Dict[str, str]:
        """批量获取下载链接"""
        return self.files.get_download_urls(file_ids)

    def download_file(self, file_id: str, save_path: str = None, **kwargs) -> str:
        """下载文件"""
        return self.files.download_file(file_id, save_path, **kwargs)

    def download_files(self, file_ids: List[str], save_dir: str = "downloads", **kwargs) -> List[str]:
        """批量下载文件"""
        return self.files.download_files(file_ids, save_dir, **kwargs)

    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储空间信息"""
        return self.files.get_storage_info()

    def list_files_with_details(self, **kwargs) -> Dict[str, Any]:
        """获取文件列表（增强版）"""
        return self.files.list_files_with_details(**kwargs)

    def search_files_advanced(self, keyword: str, **kwargs) -> Dict[str, Any]:
        """高级文件搜索"""
        return self.files.search_files_advanced(keyword, **kwargs)


    
    def create_folder(self, folder_name: str, parent_id: str = "0") -> Dict[str, Any]:
        """创建文件夹"""
        return self.files.create_folder(folder_name, parent_id)
    
    def delete_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """删除文件"""
        return self.files.delete_files(file_ids)
    
    def move_files(self, file_ids: List[str], target_folder_id: str) -> Dict[str, Any]:
        """移动文件"""
        return self.files.move_files(file_ids, target_folder_id)
    
    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """重命名文件"""
        return self.files.rename_file(file_id, new_name)
    
    def search_files(self, keyword: str, **kwargs) -> Dict[str, Any]:
        """搜索文件"""
        return self.files.search_files(keyword, **kwargs)
    
    def get_download_url(self, file_id: str) -> str:
        """获取下载链接"""
        return self.files.get_download_url(file_id)
    
    # 分享管理快捷方法
    def create_share(self, file_ids: List[str], **kwargs) -> Dict[str, Any]:
        """创建分享"""
        return self.shares.create_share(file_ids, **kwargs)
    
    def parse_share_url(self, share_url: str):
        """解析分享链接"""
        return self.shares.parse_share_url(share_url)
    
    def save_shared_files(self, share_url: str, target_folder_id: str = "0", **kwargs) -> Dict[str, Any]:
        """转存分享文件"""
        return self.shares.parse_and_save(share_url, target_folder_id, **kwargs)
    
    def get_my_shares(self, **kwargs) -> Dict[str, Any]:
        """获取我的分享"""
        return self.shares.get_my_shares(**kwargs)
    
    # 高级功能
    def batch_save_shares(
        self,
        share_urls: List[str],
        target_folder_id: str = "0",
        create_subfolder: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量转存分享链接
        
        Args:
            share_urls: 分享链接列表
            target_folder_id: 目标文件夹ID
            create_subfolder: 是否为每个分享创建子文件夹
            
        Returns:
            转存结果列表
        """
        results = []
        
        for i, share_url in enumerate(share_urls):
            try:
                # 如果需要创建子文件夹，生成文件夹名
                folder_name = None
                if create_subfolder:
                    folder_name = f"分享_{i+1}"
                
                result = self.save_shared_files(
                    share_url,
                    target_folder_id,
                    target_folder_name=folder_name
                )
                
                results.append({
                    'success': True,
                    'share_url': share_url,
                    'result': result
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'share_url': share_url,
                    'error': str(e)
                })
        
        return results
    
    def sync_folder(
        self,
        local_path: str,
        remote_folder_id: str = "0",
        upload_new: bool = True,
        delete_remote: bool = False
    ) -> Dict[str, Any]:
        """
        同步本地文件夹到云端（占位符，需要实现上传功能）
        
        Args:
            local_path: 本地文件夹路径
            remote_folder_id: 远程文件夹ID
            upload_new: 是否上传新文件
            delete_remote: 是否删除远程多余文件
            
        Returns:
            同步结果
        """
        # TODO: 实现文件上传和同步逻辑
        raise NotImplementedError("文件同步功能待实现")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储空间信息
        
        Returns:
            存储信息
        """
        try:
            response = self.api_client.get('capacity')
            return response
        except Exception as e:
            return {'error': str(e)}
    
    def close(self):
        """关闭客户端"""
        self.api_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def create_client(cookies: Optional[str] = None, auto_login: bool = True) -> QuarkClient:
    """创建夸克网盘客户端的便捷函数"""
    return QuarkClient(cookies=cookies, auto_login=auto_login)
