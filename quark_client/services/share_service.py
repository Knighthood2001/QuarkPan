"""
分享服务
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs

from ..core.api_client import QuarkAPIClient
from ..config import Config
from ..exceptions import APIError, ShareLinkError


class ShareService:
    """分享服务"""
    
    def __init__(self, client: QuarkAPIClient):
        """
        初始化分享服务
        
        Args:
            client: API客户端实例
        """
        self.client = client
    
    def create_share(
        self,
        file_ids: List[str],
        expire_days: int = 7,
        password: Optional[str] = None,
        download_limit: int = 0
    ) -> Dict[str, Any]:
        """
        创建分享链接
        
        Args:
            file_ids: 文件ID列表
            expire_days: 过期天数，0表示永久
            password: 提取码，None表示无密码
            download_limit: 下载次数限制，0表示无限制
            
        Returns:
            分享信息
        """
        data = {
            'fid_list': file_ids,
            'title': '',
            'url_type': 1,
            'expired_type': 1 if expire_days > 0 else 0,
            'expired_at': expire_days * 24 * 3600 if expire_days > 0 else 0,
            'passcode': password or '',
            'download_limit_count': download_limit
        }
        
        response = self.client.post('share', json_data=data)
        return response
    
    def parse_share_url(self, share_url: str) -> Tuple[str, Optional[str]]:
        """
        解析分享链接，提取分享ID和密码
        
        Args:
            share_url: 分享链接
            
        Returns:
            (share_id, password) 元组
            
        Raises:
            ShareLinkError: 链接格式错误
        """
        # 支持多种分享链接格式
        patterns = [
            # 夸克网盘标准格式
            r'https://pan\.quark\.cn/s/([a-zA-Z0-9]+)',
            # 带密码的格式
            r'https://pan\.quark\.cn/s/([a-zA-Z0-9]+).*?密码[：:]?\s*([a-zA-Z0-9]+)',
            # 其他可能的格式
            r'quark://share/([a-zA-Z0-9]+)',
        ]
        
        share_id = None
        password = None
        
        for pattern in patterns:
            match = re.search(pattern, share_url, re.IGNORECASE)
            if match:
                share_id = match.group(1)
                if len(match.groups()) > 1:
                    password = match.group(2)
                break
        
        if not share_id:
            raise ShareLinkError(f"无法解析分享链接: {share_url}")
        
        # 尝试从文本中提取密码
        if not password:
            password_patterns = [
                r'密码[：:]?\s*([a-zA-Z0-9]+)',
                r'提取码[：:]?\s*([a-zA-Z0-9]+)',
                r'code[：:]?\s*([a-zA-Z0-9]+)',
            ]
            
            for pattern in password_patterns:
                match = re.search(pattern, share_url, re.IGNORECASE)
                if match:
                    password = match.group(1)
                    break
        
        return share_id, password
    
    def get_share_token(self, share_id: str, password: Optional[str] = None) -> str:
        """
        获取分享访问令牌
        
        Args:
            share_id: 分享ID
            password: 提取码
            
        Returns:
            访问令牌
        """
        data = {
            'pwd_id': share_id,
            'passcode': password or ''
        }
        
        # 使用分享专用的API基础URL
        response = self.client.post(
            'share/sharepage/token',
            json_data=data,
            base_url=Config.SHARE_BASE_URL
        )
        
        # 提取token
        if isinstance(response, dict) and 'data' in response:
            token_info = response['data']
            return token_info.get('stoken', '')
        
        raise ShareLinkError("无法获取分享访问令牌")
    
    def get_share_info(self, share_id: str, token: str) -> Dict[str, Any]:
        """
        获取分享详细信息
        
        Args:
            share_id: 分享ID
            token: 访问令牌
            
        Returns:
            分享信息
        """
        params = {
            'pwd_id': share_id,
            'stoken': token,
            '_page': 1,
            '_size': 50,
            '_sort': 'file_name:asc'
        }
        
        response = self.client.get(
            'share/sharepage/detail',
            params=params,
            base_url=Config.SHARE_BASE_URL
        )
        
        return response
    
    def save_shared_files(
        self,
        share_id: str,
        token: str,
        file_ids: List[str],
        target_folder_id: str = "0",
        target_folder_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        转存分享的文件
        
        Args:
            share_id: 分享ID
            token: 访问令牌
            file_ids: 要转存的文件ID列表
            target_folder_id: 目标文件夹ID
            target_folder_name: 目标文件夹名称（如果需要创建新文件夹）
            
        Returns:
            转存结果
        """
        data = {
            'fid_list': file_ids,
            'fid_token_list': [{'fid': fid, 'token': token} for fid in file_ids],
            'to_pdir_fid': target_folder_id,
            'pwd_id': share_id,
            'stoken': token,
            'pdir_fid': "0",
            'scene': 'link'
        }
        
        # 如果指定了目标文件夹名称，添加到请求中
        if target_folder_name:
            data['to_pdir_name'] = target_folder_name
        
        response = self.client.post(
            'share/sharepage/save',
            json_data=data,
            base_url=Config.SHARE_BASE_URL
        )
        
        return response
    
    def parse_and_save(
        self,
        share_url: str,
        target_folder_id: str = "0",
        target_folder_name: Optional[str] = None,
        file_filter: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        解析分享链接并转存文件（一站式服务）
        
        Args:
            share_url: 分享链接
            target_folder_id: 目标文件夹ID
            target_folder_name: 目标文件夹名称
            file_filter: 文件过滤函数，接收文件信息字典，返回True表示转存
            
        Returns:
            转存结果
        """
        # 1. 解析分享链接
        share_id, password = self.parse_share_url(share_url)
        
        # 2. 获取访问令牌
        token = self.get_share_token(share_id, password)
        
        # 3. 获取分享信息
        share_info = self.get_share_info(share_id, token)
        
        # 4. 提取文件列表
        if not isinstance(share_info, dict) or 'data' not in share_info:
            raise ShareLinkError("无法获取分享文件列表")
        
        files = share_info['data'].get('list', [])
        if not files:
            raise ShareLinkError("分享中没有文件")
        
        # 5. 应用文件过滤器
        if file_filter:
            files = [f for f in files if file_filter(f)]
        
        if not files:
            raise ShareLinkError("没有符合条件的文件")
        
        # 6. 提取文件ID
        file_ids = [f['fid'] for f in files]
        
        # 7. 转存文件
        result = self.save_shared_files(
            share_id, token, file_ids, target_folder_id, target_folder_name
        )
        
        # 8. 添加额外信息到结果中
        result['share_info'] = {
            'share_id': share_id,
            'file_count': len(files),
            'files': files
        }
        
        return result
    
    def get_my_shares(self, page: int = 1, size: int = 50) -> Dict[str, Any]:
        """
        获取我的分享列表
        
        Args:
            page: 页码
            size: 每页数量
            
        Returns:
            分享列表
        """
        params = {
            '_page': page,
            '_size': size,
            '_sort': 'created_at:desc'
        }
        
        response = self.client.get('share', params=params)
        return response
    
    def delete_share(self, share_id: str) -> Dict[str, Any]:
        """
        删除分享
        
        Args:
            share_id: 分享ID
            
        Returns:
            删除结果
        """
        data = {'share_id': share_id}
        
        response = self.client.post('share/delete', json_data=data)
        return response
