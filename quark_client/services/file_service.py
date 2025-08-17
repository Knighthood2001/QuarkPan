"""
文件管理服务
"""

from typing import Dict, List, Optional, Any
from ..core.api_client import QuarkAPIClient
from ..exceptions import APIError, FileNotFoundError


class FileService:
    """文件管理服务"""
    
    def __init__(self, client: QuarkAPIClient):
        """
        初始化文件服务
        
        Args:
            client: API客户端实例
        """
        self.client = client
    
    def list_files(
        self,
        folder_id: str = "0",
        page: int = 1,
        size: int = 50,
        sort_field: str = "file_name",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        获取文件列表
        
        Args:
            folder_id: 文件夹ID，"0"表示根目录
            page: 页码，从1开始
            size: 每页数量
            sort_field: 排序字段 (file_name, file_size, updated_at等)
            sort_order: 排序方向 (asc, desc)
            
        Returns:
            包含文件列表的字典
        """
        params = {
            'pdir_fid': folder_id,
            '_page': page,
            '_size': size,
            '_sort': f"{sort_field}:{sort_order}"
        }
        
        try:
            response = self.client.get('file/sort', params=params)
            return response
        except APIError as e:
            if 'not found' in str(e).lower():
                raise FileNotFoundError(f"文件夹不存在: {folder_id}")
            raise
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件详细信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件信息字典
        """
        params = {'fids': file_id}
        
        try:
            response = self.client.get('file', params=params)
            
            # 检查响应格式
            if isinstance(response, dict) and 'data' in response:
                files = response['data']
                if files and len(files) > 0:
                    return files[0]
            
            raise FileNotFoundError(f"文件不存在: {file_id}")
            
        except APIError as e:
            if 'not found' in str(e).lower():
                raise FileNotFoundError(f"文件不存在: {file_id}")
            raise
    
    def create_folder(self, folder_name: str, parent_id: str = "0") -> Dict[str, Any]:
        """
        创建文件夹
        
        Args:
            folder_name: 文件夹名称
            parent_id: 父文件夹ID，"0"表示根目录
            
        Returns:
            创建结果
        """
        data = {
            'pdir_fid': parent_id,
            'file_name': folder_name,
            'dir_init_lock': False,
            'dir_path': ''
        }
        
        response = self.client.post('file', json_data=data)
        return response
    
    def delete_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        删除文件/文件夹
        
        Args:
            file_ids: 文件ID列表
            
        Returns:
            删除结果
        """
        data = {
            'action_type': 2,  # 删除操作
            'filelist': file_ids,
            'exclude_fids': []
        }
        
        response = self.client.post('file/delete', json_data=data)
        return response
    
    def move_files(self, file_ids: List[str], target_folder_id: str) -> Dict[str, Any]:
        """
        移动文件/文件夹
        
        Args:
            file_ids: 文件ID列表
            target_folder_id: 目标文件夹ID
            
        Returns:
            移动结果
        """
        data = {
            'action_type': 1,  # 移动操作
            'filelist': file_ids,
            'target_fid': target_folder_id,
            'exclude_fids': []
        }
        
        response = self.client.post('file/move', json_data=data)
        return response
    
    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """
        重命名文件/文件夹
        
        Args:
            file_id: 文件ID
            new_name: 新名称
            
        Returns:
            重命名结果
        """
        data = {
            'fid': file_id,
            'file_name': new_name
        }
        
        response = self.client.post('file/rename', json_data=data)
        return response
    
    def get_download_url(self, file_id: str) -> str:
        """
        获取文件下载链接
        
        Args:
            file_id: 文件ID
            
        Returns:
            下载链接
        """
        params = {'fids': file_id}
        
        response = self.client.get('file/download', params=params)
        
        # 解析下载链接
        if isinstance(response, dict) and 'data' in response:
            data = response['data']
            if data and len(data) > 0:
                download_info = data[0]
                return download_info.get('download_url', '')
        
        raise APIError("无法获取下载链接")
    
    def search_files(
        self,
        keyword: str,
        folder_id: str = "0",
        page: int = 1,
        size: int = 50
    ) -> Dict[str, Any]:
        """
        搜索文件
        
        Args:
            keyword: 搜索关键词
            folder_id: 搜索范围文件夹ID，"0"表示全盘搜索
            page: 页码
            size: 每页数量
            
        Returns:
            搜索结果
        """
        params = {
            'keyword': keyword,
            'pdir_fid': folder_id,
            '_page': page,
            '_size': size
        }
        
        response = self.client.get('file/search', params=params)
        return response
    
    def get_folder_tree(self, folder_id: str = "0", max_depth: int = 3) -> Dict[str, Any]:
        """
        获取文件夹树结构
        
        Args:
            folder_id: 根文件夹ID
            max_depth: 最大深度
            
        Returns:
            文件夹树结构
        """
        params = {
            'pdir_fid': folder_id,
            'max_depth': max_depth
        }
        
        response = self.client.get('file/tree', params=params)
        return response
