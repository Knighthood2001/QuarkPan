"""
分享服务
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config import Config
from ..core.api_client import QuarkAPIClient
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
        title: str = "",
        expire_days: int = 0,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建分享链接

        Args:
            file_ids: 文件ID列表
            title: 分享标题
            expire_days: 过期天数，0表示永久
            password: 提取码，None表示无密码

        Returns:
            分享信息，包含分享链接
        """
        import time

        # 第一步：创建分享任务
        data = {
            'fid_list': file_ids,
            'title': title,
            'url_type': 1,  # 公开链接
            'expired_type': 1 if expire_days == 0 else 0  # 1=永久，0=有期限
        }

        # 如果设置了密码，添加密码字段
        if password:
            data['passcode'] = password

        response = self.client.post('share', json_data=data)

        if not response.get('status') == 200:
            raise APIError(f"创建分享失败: {response.get('message', '未知错误')}")

        # 获取任务ID
        task_id = response.get('data', {}).get('task_id')
        if not task_id:
            raise APIError("无法获取分享任务ID")

        # 第二步：轮询任务状态，等待分享创建完成
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            task_response = self.client.get(
                'task',
                params={
                    'task_id': task_id,
                    'retry_index': retry_count
                }
            )

            if task_response.get('status') == 200:
                task_data = task_response.get('data', {})

                # 检查任务状态
                if task_data.get('status') == 2:  # 任务完成
                    share_id = task_data.get('share_id')
                    if share_id:
                        # 第三步：获取完整的分享信息
                        return self._get_share_details(share_id)
                elif task_data.get('status') == 3:  # 任务失败
                    raise APIError(f"分享创建失败: {task_data.get('message', '任务失败')}")

            retry_count += 1
            time.sleep(1)  # 等待1秒后重试

        raise APIError("分享创建超时")

    def _get_share_details(self, share_id: str) -> Dict[str, Any]:
        """
        获取分享详细信息，包括分享链接

        Args:
            share_id: 分享ID

        Returns:
            完整的分享信息
        """
        data = {'share_id': share_id}

        response = self.client.post('share/password', json_data=data)

        if not response.get('status') == 200:
            raise APIError(f"获取分享详情失败: {response.get('message', '未知错误')}")

        return response.get('data', {})

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
            '_order_field': 'created_at',
            '_order_type': 'desc',  # 降序
            '_fetch_total': 1,
            '_fetch_notify_follow': 1
        }

        response = self.client.get('share/mypage/detail', params=params)
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
        file_filter: Optional[Callable] = None
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
