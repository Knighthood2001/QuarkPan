# -*- coding: utf-8 -*-
"""
文件管理服务
"""

from typing import Any, Dict, List, Optional

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
        if not file_id or file_id == "0":
            raise ValueError("无效的文件ID")

        params = {'fids': file_id}

        try:
            response = self.client.get('file', params=params)

            # 检查响应格式
            if isinstance(response, dict) and 'data' in response:
                data = response['data']
                if isinstance(data, dict) and 'list' in data:
                    file_list = data['list']
                    if file_list and len(file_list) > 0:
                        # 查找匹配的文件ID
                        for file_info in file_list:
                            if file_info.get('fid') == file_id:
                                return file_info

                        # 如果没有找到精确匹配，返回第一个
                        return file_list[0]
                elif isinstance(data, list) and len(data) > 0:
                    # 兼容旧格式
                    return data[0]

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

        # 添加查询参数
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        response = self.client.post('file', json_data=data, params=params)
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

        # 添加查询参数
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        response = self.client.post('file/delete', json_data=data, params=params)
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

        # 添加查询参数
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        response = self.client.post('file/rename', json_data=data, params=params)
        return response

    def search_files(
        self,
        keyword: str,
        folder_id: str = "0",
        page: int = 1,
        size: int = 50,
        sort_field: str = "file_type",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        搜索文件

        Args:
            keyword: 搜索关键词
            folder_id: 搜索范围文件夹ID，"0"表示全盘搜索（暂不支持）
            page: 页码
            size: 每页数量
            sort_field: 排序字段
            sort_order: 排序方向

        Returns:
            搜索结果
        """
        params = {
            'q': keyword,
            '_page': page,
            '_size': size,
            '_fetch_total': 1,
            '_sort': f'{sort_field}:{sort_order},updated_at:desc',
            '_is_hl': 1  # 启用高亮
        }

        # 注意：夸克网盘的搜索API似乎不支持文件夹范围限制
        _ = folder_id  # folder_id参数暂时不使用

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

    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储空间信息

        Returns:
            存储空间信息
        """
        response = self.client.get('capacity')
        return response

    def list_files_with_details(
        self,
        folder_id: str = "0",
        page: int = 1,
        size: int = 50,
        sort_field: str = "file_name",
        sort_order: str = "asc",
        include_folders: bool = True,
        include_files: bool = True
    ) -> Dict[str, Any]:
        """
        获取文件列表（增强版，支持过滤）

        Args:
            folder_id: 文件夹ID，"0"表示根目录
            page: 页码，从1开始
            size: 每页数量
            sort_field: 排序字段
            sort_order: 排序方向
            include_folders: 是否包含文件夹
            include_files: 是否包含文件

        Returns:
            包含文件列表的字典
        """
        response = self.list_files(folder_id, page, size, sort_field, sort_order)

        # 如果需要过滤，则处理响应数据
        if not include_folders or not include_files:
            if isinstance(response, dict) and 'data' in response:
                file_list = response['data'].get('list', [])
                filtered_list = []

                for file_info in file_list:
                    file_type = file_info.get('file_type', 0)
                    is_folder = file_type == 0

                    if (is_folder and include_folders) or (not is_folder and include_files):
                        filtered_list.append(file_info)

                response['data']['list'] = filtered_list
                response['data']['filtered_total'] = len(filtered_list)

        return response

    def search_files_advanced(
        self,
        keyword: str,
        folder_id: str = "0",
        page: int = 1,
        size: int = 50,
        file_extensions: Optional[List[str]] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        sort_field: str = "file_type",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        高级文件搜索（客户端过滤）

        Args:
            keyword: 搜索关键词
            folder_id: 搜索范围文件夹ID（暂不支持）
            page: 页码
            size: 每页数量
            file_extensions: 文件扩展名过滤 (如: ['pdf', 'doc', 'txt'])
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            sort_field: 排序字段
            sort_order: 排序方向

        Returns:
            搜索结果
        """
        # 如果没有过滤条件，直接返回基础搜索结果
        if not file_extensions and min_size is None and max_size is None:
            return self.search_files(keyword, folder_id, page, size, sort_field, sort_order)

        # 获取更多结果用于客户端过滤
        search_size = max(size * 3, 100)
        response = self.search_files(keyword, folder_id, 1, search_size, sort_field, sort_order)

        # 应用客户端过滤器
        if isinstance(response, dict) and 'data' in response:
            file_list = response['data'].get('list', [])
            filtered_list = []

            for file_info in file_list:
                # 文件扩展名过滤
                if file_extensions:
                    file_name = file_info.get('file_name', '').lower()
                    file_ext = file_name.split('.')[-1] if '.' in file_name else ''
                    if file_ext not in [ext.lower() for ext in file_extensions]:
                        continue

                # 文件大小过滤
                file_size = file_info.get('size', 0)
                if min_size is not None and file_size < min_size:
                    continue
                if max_size is not None and file_size > max_size:
                    continue

                filtered_list.append(file_info)

            # 应用分页到过滤后的结果
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_list = filtered_list[start_idx:end_idx]

            response['data']['list'] = paginated_list
            response['data']['filtered_total'] = len(filtered_list)
            # 更新metadata中的总数
            if 'metadata' in response:
                response['metadata']['_total'] = len(filtered_list)
                response['metadata']['_count'] = len(paginated_list)

        return response

    def get_file_path(self, file_id: str) -> str:
        """
        获取文件的完整路径

        Args:
            file_id: 文件ID

        Returns:
            文件路径字符串
        """
        try:
            file_info = self.get_file_info(file_id)
            # 这里需要根据实际API响应结构来获取路径
            # 可能需要递归获取父文件夹信息来构建完整路径
            return file_info.get('file_path', file_info.get('file_name', ''))
        except Exception:
            return ""

    def move_files(
        self,
        file_ids: List[str],
        target_folder_id: str,
        exclude_fids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        移动文件到指定文件夹

        Args:
            file_ids: 要移动的文件ID列表
            target_folder_id: 目标文件夹ID
            exclude_fids: 排除的文件ID列表

        Returns:
            移动结果
        """
        data = {
            'action_type': 1,  # 移动操作
            'to_pdir_fid': target_folder_id,
            'filelist': file_ids,
            'exclude_fids': exclude_fids or []
        }

        response = self.client.post('file/move', json_data=data)

        if not response.get('status') == 200:
            raise APIError(f"移动文件失败: {response.get('message', '未知错误')}")

        data = response.get('data', {})
        task_id = data.get('task_id')
        finish = data.get('finish', False)

        if finish:
            # 同步完成，直接返回结果
            return response
        elif task_id:
            # 异步任务，需要轮询状态
            return self._wait_for_move_task(task_id, response.get('metadata', {}).get('tq_gap', 500))
        else:
            raise APIError("移动任务创建失败，无法获取任务ID")

    def _wait_for_move_task(self, task_id: str, poll_interval: int = 500) -> Dict[str, Any]:
        """
        等待移动任务完成

        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔（毫秒）

        Returns:
            任务完成结果
        """
        import time

        max_retries = 30  # 最多等待15秒
        retry_count = 0

        while retry_count < max_retries:
            try:
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
                        return task_response
                    elif task_data.get('status') == 3:  # 任务失败
                        raise APIError(f"移动任务失败: {task_data.get('message', '任务失败')}")

                retry_count += 1
                time.sleep(poll_interval / 1000)  # 转换为秒

            except Exception as e:
                if retry_count >= max_retries - 1:
                    raise APIError(f"移动任务轮询失败: {e}")
                retry_count += 1
                time.sleep(poll_interval / 1000)

        raise APIError("移动任务超时")
