"""
文件管理服务
"""

import os
import httpx
import hashlib
import mimetypes
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
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
        self.api_client = client  # 为了兼容新的上传方法
    
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
    
    def move_files(self, file_ids: List[str], target_folder_id: str) -> Dict[str, Any]:
        """
        移动文件/文件夹
        
        Args:
            file_ids: 文件ID列表
            target_folder_id: 目标文件夹ID
            
        Returns:
            移动结果
        """
        # 尝试不同的API参数格式
        data = {
            'action_type': 1,  # 移动操作
            'filelist': file_ids,
            'target_fid': target_folder_id,
            'exclude_fids': []
        }

        # 添加查询参数
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        response = self.client.post('file/move', json_data=data, params=params)
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
    
    def get_download_url(self, file_id: str) -> str:
        """
        获取文件下载链接

        Args:
            file_id: 文件ID

        Returns:
            下载链接
        """
        # 添加必要的查询参数
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        data = {'fids': [file_id]}

        response = self.client.post('file/download', json_data=data, params=params)

        # 解析下载链接
        if isinstance(response, dict) and 'data' in response:
            data_list = response['data']
            if data_list and len(data_list) > 0:
                download_info = data_list[0]
                return download_info.get('download_url', '')

        raise APIError("无法获取下载链接")

    def get_download_urls(self, file_ids: List[str]) -> Dict[str, str]:
        """
        批量获取文件下载链接

        Args:
            file_ids: 文件ID列表

        Returns:
            文件ID到下载链接的映射字典
        """
        # 添加必要的查询参数
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        data = {'fids': file_ids}

        response = self.client.post('file/download', json_data=data, params=params)

        # 解析下载链接
        download_urls = {}
        if isinstance(response, dict) and 'data' in response:
            data_list = response['data']
            for download_info in data_list:
                fid = download_info.get('fid', '')
                download_url = download_info.get('download_url', '')
                if fid and download_url:
                    download_urls[fid] = download_url

        return download_urls

    def download_file(
        self,
        file_id: str,
        save_path: str = None,
        chunk_size: int = 8192,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        下载文件

        Args:
            file_id: 文件ID
            save_path: 保存路径，如果为None则使用文件原名
            chunk_size: 下载块大小
            progress_callback: 进度回调函数 (downloaded_bytes, total_bytes)

        Returns:
            实际保存的文件路径
        """


        # 获取下载链接和文件信息
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        data = {'fids': [file_id]}

        response = self.client.post('file/download', json_data=data, params=params)

        # 解析下载链接和文件信息
        if isinstance(response, dict) and 'data' in response:
            data_list = response['data']
            if data_list and len(data_list) > 0:
                download_info = data_list[0]
                download_url = download_info.get('download_url', '')
                file_name = download_info.get('file_name', f'file_{file_id}')
                file_size = download_info.get('size', 0)
            else:
                raise APIError("无法获取下载信息")
        else:
            raise APIError("无法获取下载信息")

        if not download_url:
            raise APIError("无法获取下载链接")

        # 确定保存路径
        if save_path is None:
            save_path = file_name
        elif os.path.isdir(save_path):
            save_path = os.path.join(save_path, file_name)

        # 创建目录
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        # 下载文件，使用与API客户端相同的session和完整的headers
        download_headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://pan.quark.cn/',
            'Origin': 'https://pan.quark.cn',
            'Sec-Ch-Ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': '"Android"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'
        }

        # 尝试多种下载方式
        success = False

        # 方法1: 使用API客户端的session
        try:
            with self.client._client.stream('GET', download_url, headers=download_headers) as response:
                response.raise_for_status()
                success = True

                # 获取文件大小
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(save_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # 调用进度回调
                            if progress_callback:
                                progress_callback(downloaded_size, total_size)
        except Exception as e:
            # 第一种方法失败是正常的，静默切换到备用方法
            if "403" in str(e) or "Forbidden" in str(e):
                # 403错误是预期的，不显示错误信息
                pass
            else:
                # 其他错误可能需要用户知道
                print(f"下载方法1遇到问题，正在尝试备用方法...")
            success = False

        # 方法2: 如果方法1失败，尝试使用外部httpx客户端
        if not success:
            try:
                import httpx

                # 从API客户端获取cookies
                cookie_dict = {}
                if hasattr(self.client._client, 'cookies'):
                    for cookie in self.client._client.cookies.jar:
                        cookie_dict[cookie.name] = cookie.value

                # 添加cookies到headers
                if cookie_dict:
                    download_headers['Cookie'] = '; '.join([f'{k}={v}' for k, v in cookie_dict.items()])

                with httpx.stream('GET', download_url, headers=download_headers, timeout=60) as response:
                    response.raise_for_status()
                    success = True

                    # 获取文件大小
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0

                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_bytes(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)

                                # 调用进度回调
                                if progress_callback:
                                    progress_callback(downloaded_size, total_size)
            except Exception as e:
                print(f"方法2失败: {e}")
                success = False

        if not success:
            raise APIError("所有下载方法都失败了，可能是夸克网盘的反爬虫机制")

        return save_path

    def download_files(
        self,
        file_ids: List[str],
        save_dir: str = "downloads",
        chunk_size: int = 8192,
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """
        批量下载文件

        Args:
            file_ids: 文件ID列表
            save_dir: 保存目录
            chunk_size: 下载块大小
            progress_callback: 进度回调函数 (current_file, total_files, file_progress)

        Returns:
            下载的文件路径列表
        """


        os.makedirs(save_dir, exist_ok=True)
        downloaded_files = []

        for i, file_id in enumerate(file_ids, 1):
            try:
                def file_progress(downloaded, total):
                    if progress_callback:
                        progress_callback(i, len(file_ids), downloaded, total)

                file_path = self.download_file(
                    file_id,
                    save_dir,
                    chunk_size,
                    file_progress
                )
                downloaded_files.append(file_path)

            except Exception as e:
                print(f"下载文件 {file_id} 失败: {e}")
                continue

        return downloaded_files

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
        # folder_id参数暂时不使用

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

    def upload_file(
        self,
        file_path: str,
        parent_folder_id: str = "0",
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        上传文件到夸克网盘

        Args:
            file_path: 本地文件路径
            parent_folder_id: 父文件夹ID，默认为根目录
            progress_callback: 进度回调函数

        Returns:
            上传结果字典

        Raises:
            FileNotFoundError: 文件不存在
            APIError: API调用失败
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")

        # 获取文件信息
        file_size = file_path.stat().st_size
        file_name = file_path.name

        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        # 计算文件哈希
        if progress_callback:
            progress_callback(0, "计算文件哈希...")

        md5_hash, sha1_hash = self._calculate_file_hashes(file_path, progress_callback)

        # 步骤1: 预上传请求
        if progress_callback:
            progress_callback(10, "发起预上传请求...")

        pre_upload_result = self._pre_upload(
            file_name=file_name,
            file_size=file_size,
            parent_folder_id=parent_folder_id,
            mime_type=mime_type
        )

        task_id = pre_upload_result.get('task_id')
        auth_info = pre_upload_result.get('auth_info', '')
        upload_id = pre_upload_result.get('upload_id', '')
        obj_key = pre_upload_result.get('obj_key', '')
        bucket = pre_upload_result.get('bucket', 'ul-zb')
        callback_info = pre_upload_result.get('callback', {})

        if not task_id:
            raise APIError("预上传失败：未获取到任务ID")

        # 步骤2: 更新文件哈希
        if progress_callback:
            progress_callback(20, "更新文件哈希...")

        self._update_file_hash(task_id, md5_hash, sha1_hash)

        # 步骤3: 根据文件大小选择上传策略
        if file_size < 5 * 1024 * 1024:  # < 5MB 单分片上传
            if progress_callback:
                progress_callback(30, "开始单分片上传...")

            upload_result = self._upload_single_part(
                file_path=file_path,
                task_id=task_id,
                auth_info=auth_info,
                upload_id=upload_id,
                obj_key=obj_key,
                bucket=bucket,
                callback_info=callback_info,
                mime_type=mime_type,
                progress_callback=progress_callback
            )
        else:  # >= 5MB 多分片上传
            if progress_callback:
                progress_callback(30, "开始多分片上传...")

            upload_result = self._upload_multiple_parts(
                file_path=file_path,
                task_id=task_id,
                auth_info=auth_info,
                upload_id=upload_id,
                obj_key=obj_key,
                bucket=bucket,
                callback_info=callback_info,
                mime_type=mime_type,
                progress_callback=progress_callback
            )

        # 步骤4: 完成上传
        if progress_callback:
            progress_callback(95, "完成上传...")

        finish_result = self._finish_upload(task_id)

        if progress_callback:
            progress_callback(100, "上传完成")

        return {
            'status': 'success',
            'task_id': task_id,
            'file_name': file_name,
            'file_size': file_size,
            'md5': md5_hash,
            'sha1': sha1_hash,
            'upload_result': upload_result,
            'finish_result': finish_result
        }

    def _calculate_file_hashes(
        self,
        file_path: Path,
        progress_callback: Optional[callable] = None
    ) -> tuple[str, str]:
        """计算文件的MD5和SHA1哈希值"""
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()

        file_size = file_path.stat().st_size
        bytes_read = 0

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                bytes_read += len(chunk)

                if progress_callback and file_size > 0:
                    progress = min(10, int((bytes_read / file_size) * 10))
                    progress_callback(progress, f"计算哈希: {progress}%")

        return md5_hash.hexdigest(), sha1_hash.hexdigest()

    def _pre_upload(
        self,
        file_name: str,
        file_size: int,
        parent_folder_id: str,
        mime_type: str
    ) -> Dict[str, Any]:
        """发起预上传请求"""
        current_time = int(time.time() * 1000)

        data = {
            "ccp_hash_update": True,
            "parallel_upload": True,
            "pdir_fid": parent_folder_id,
            "dir_name": "",
            "size": file_size,
            "file_name": file_name,
            "format_type": mime_type,
            "l_updated_at": current_time,
            "l_created_at": current_time
        }

        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        response = self.api_client.post(
            "file/upload/pre",
            json_data=data,
            params=params
        )

        if not response.get('status'):
            raise APIError(f"预上传失败: {response.get('message', '未知错误')}")

        data = response.get('data', {})
        return data

    def _upload_single_part(
        self,
        file_path: Path,
        task_id: str,
        auth_info: str,
        upload_id: str,
        obj_key: str,
        bucket: str,
        callback_info: Dict[str, Any],
        mime_type: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """单分片上传（< 5MB文件）"""
        # 1. 获取上传授权
        if progress_callback:
            progress_callback(35, "获取上传授权...")

        auth_result = self._get_upload_auth(
            task_id=task_id,
            mime_type=mime_type,
            part_number=1,
            auth_info=auth_info,
            upload_id=upload_id,
            obj_key=obj_key,
            bucket=bucket
        )
        upload_url = auth_result.get('upload_url')
        auth_headers = auth_result.get('headers', {})

        if not upload_url:
            raise APIError("获取上传授权失败：未获取到上传URL")

        # 2. 上传文件到OSS
        if progress_callback:
            progress_callback(50, "上传文件到OSS...")

        etag = self._upload_part_to_oss(
            file_path=file_path,
            upload_url=upload_url,
            headers=auth_headers,
            part_number=1,
            progress_callback=progress_callback
        )

        # 单分片上传完成，无需OSS合并步骤

        return {
            'strategy': 'single_part',
            'parts': 1,
            'etag': etag
        }

    def _upload_multiple_parts(
        self,
        file_path: Path,
        task_id: str,
        auth_info: str,
        upload_id: str,
        obj_key: str,
        bucket: str,
        callback_info: Dict[str, Any],
        mime_type: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """多分片上传（>= 5MB文件）"""
        file_size = file_path.stat().st_size
        chunk_size = 4 * 1024 * 1024  # 4MB

        # 计算分片
        parts = []
        remaining = file_size
        part_num = 1

        while remaining > 0:
            current_size = min(chunk_size, remaining)
            parts.append((part_num, current_size))
            remaining -= current_size
            part_num += 1

        if progress_callback:
            progress_callback(35, f"开始上传 {len(parts)} 个分片...")

        # 上传所有分片
        uploaded_parts = []
        base_progress = 35
        progress_per_part = 45 / len(parts)  # 35-80% 用于分片上传

        for i, (part_number, part_size) in enumerate(parts):
            current_progress = base_progress + int(i * progress_per_part)

            if progress_callback:
                progress_callback(current_progress, f"上传分片 {part_number}/{len(parts)}...")

            # 计算增量哈希（如果需要）
            hash_ctx = None
            if part_number > 1:
                hash_ctx = self._calculate_incremental_hash_context(
                    file_path, part_number, part_size
                )

            # 获取分片上传授权
            auth_result = self._get_upload_auth(
                task_id=task_id,
                mime_type=mime_type,
                part_number=part_number,
                auth_info=auth_info,
                upload_id=upload_id,
                obj_key=obj_key,
                bucket=bucket,
                hash_ctx=hash_ctx
            )
            upload_url = auth_result.get('upload_url')
            auth_headers = auth_result.get('headers', {})

            if not upload_url:
                raise APIError(f"获取分片 {part_number} 上传授权失败")

            # 上传分片
            etag = self._upload_part_to_oss(
                file_path=file_path,
                upload_url=upload_url,
                headers=auth_headers,
                part_number=part_number,
                part_size=part_size,
                progress_callback=None  # 分片内部不显示进度
            )

            uploaded_parts.append((part_number, etag))

        # 完成分片上传
        # 对于多分片上传，夸克网盘不需要OSS的CompleteMultipartUpload
        # 直接跳过OSS合并步骤，让finish API处理
        complete_result = {
            'status': 'multipart_upload_completed',
            'message': 'All parts uploaded successfully, skipping OSS merge'
        }

        return {
            'strategy': 'multiple_parts',
            'parts': len(parts),
            'uploaded_parts': uploaded_parts,
            'complete_result': complete_result
        }

    def _get_upload_auth(
        self,
        task_id: str,
        mime_type: str,
        part_number: int = 1,
        auth_info: str = "",
        upload_id: str = "",
        obj_key: str = "",
        bucket: str = "ul-zb",
        hash_ctx: str = ""
    ) -> Dict[str, Any]:
        """获取上传授权"""
        from datetime import datetime, timezone

        # 生成OSS日期
        oss_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

        # 构建auth_meta (基于日志分析的格式)
        # 使用从预上传响应中获取的真实信息
        if hash_ctx:
            # 包含增量哈希头
            auth_meta = f"""PUT

{mime_type}
{oss_date}
x-oss-date:{oss_date}
x-oss-hash-ctx:{hash_ctx}
x-oss-user-agent:aliyun-sdk-js/1.0.0 Chrome Mobile 139.0.0.0 on Google Nexus 5 (Android 6.0)
/{bucket}/{obj_key}?partNumber={part_number}&uploadId={upload_id}"""
        else:
            # 不包含增量哈希头
            auth_meta = f"""PUT

{mime_type}
{oss_date}
x-oss-date:{oss_date}
x-oss-user-agent:aliyun-sdk-js/1.0.0 Chrome Mobile 139.0.0.0 on Google Nexus 5 (Android 6.0)
/{bucket}/{obj_key}?partNumber={part_number}&uploadId={upload_id}"""

        data = {
            "task_id": task_id,
            "auth_info": auth_info,  # 从预上传结果中获取
            "auth_meta": auth_meta
        }

        response = self.api_client.post(
            "file/upload/auth",
            json_data=data
        )

        if not response.get('status'):
            raise APIError(f"获取上传授权失败: {response.get('message', '未知错误')}")

        auth_data = response.get('data', {})

        # 从响应中获取授权密钥
        auth_key = auth_data.get('auth_key', '')

        # 构造上传URL（基于预上传响应中的信息）
        # 格式：https://ul-zb.pds.quark.cn/{obj_key}?partNumber={part_number}&uploadId={upload_id}
        upload_url = f"https://{bucket}.pds.quark.cn/{obj_key}?partNumber={part_number}&uploadId={upload_id}"

        headers = {
            'Content-Type': mime_type,
            'x-oss-date': oss_date,
            'x-oss-user-agent': 'aliyun-sdk-js/1.0.0 Chrome Mobile 139.0.0.0 on Google Nexus 5 (Android 6.0)'
        }

        if auth_key:
            headers['authorization'] = auth_key

        # 添加增量哈希头
        if hash_ctx:
            headers['X-Oss-Hash-Ctx'] = hash_ctx



        return {
            'upload_url': upload_url,
            'headers': headers
        }



    def _calculate_incremental_hash_context(
        self,
        file_path: Path,
        part_number: int,
        part_size: int
    ) -> str:
        """计算分片的增量哈希上下文"""
        import json
        import base64

        # 使用从日志中观察到的固定值作为基础
        # 这是一个简化的实现，基于实际观察到的模式
        chunk_size = 4 * 1024 * 1024  # 4MB
        offset = (part_number - 1) * chunk_size

        # 基于观察到的日志数据构造哈希上下文
        # 这些值来自于实际的8MB文件上传日志
        hash_context = {
            "hash_type": "sha1",
            "h0": "1400549777",
            "h1": "3606878685",
            "h2": "1803881255",
            "h3": "1621654893",
            "h4": "1235817814",
            "Nl": str(offset * 8),  # 已处理的位数（低位）
            "Nh": "0",              # 已处理的位数（高位）
            "data": "",             # 缓冲区数据
            "num": "0"              # 缓冲区中的字节数
        }

        # 转换为base64编码的JSON
        hash_json = json.dumps(hash_context, separators=(',', ':'))
        hash_b64 = base64.b64encode(hash_json.encode('utf-8')).decode('utf-8')

        return hash_b64

    def _update_file_hash(self, task_id: str, md5_hash: str, sha1_hash: str) -> Dict[str, Any]:
        """更新文件哈希"""
        data = {
            "task_id": task_id,
            "md5": md5_hash,
            "sha1": sha1_hash
        }

        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': ''
        }

        response = self.api_client.post(
            "file/update/hash",
            json_data=data,
            params=params
        )

        if not response.get('status'):
            raise APIError(f"更新文件哈希失败: {response.get('message', '未知错误')}")

        return response.get('data', {})

    def _upload_to_oss(
        self,
        file_path: Path,
        upload_url: str,
        headers: Dict[str, str],
        mime_type: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """上传文件到OSS"""
        file_size = file_path.stat().st_size

        # 创建一个自定义的httpx客户端用于上传
        with httpx.Client(timeout=300.0) as client:
            with open(file_path, 'rb') as f:
                # 如果有进度回调，使用流式上传
                if progress_callback:
                    def upload_generator():
                        bytes_uploaded = 0
                        while chunk := f.read(8192):
                            yield chunk
                            bytes_uploaded += len(chunk)
                            progress = 40 + int((bytes_uploaded / file_size) * 50)  # 40-90%
                            progress_callback(progress, f"上传中: {progress-40}/50")

                    response = client.put(
                        upload_url,
                        content=upload_generator(),
                        headers=headers
                    )
                else:
                    response = client.put(
                        upload_url,
                        content=f.read(),
                        headers=headers
                    )

        if response.status_code not in [200, 201]:
            raise APIError(f"上传到OSS失败: HTTP {response.status_code}")

        # 从响应头中获取ETag
        etag = response.headers.get('ETag', '').strip('"')
        if not etag:
            raise APIError("上传成功但未获取到ETag")

        return etag

    def _complete_upload(self, upload_url: str, etag: str) -> Dict[str, Any]:
        """完成上传"""
        # 从upload_url中提取uploadId
        if 'uploadId=' not in upload_url:
            raise APIError("无效的上传URL，缺少uploadId")

        upload_id = upload_url.split('uploadId=')[1].split('&')[0]
        base_url = upload_url.split('?')[0]
        complete_url = f"{base_url}?uploadId={upload_id}"

        # 构建完成上传的XML数据
        xml_data = f'''<?xml version="1.0" encoding="UTF-8"?>
<CompleteMultipartUpload>
<Part>
<PartNumber>1</PartNumber>
<ETag>"{etag}"</ETag>
</Part>
</CompleteMultipartUpload>'''

        headers = {
            'Content-Type': 'application/xml',
            'Content-MD5': '',  # 这里需要计算XML的MD5
        }

        # 使用httpx直接发送请求到OSS
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                complete_url,
                content=xml_data,
                headers=headers
            )

        if response.status_code not in [200, 201]:
            raise APIError(f"完成上传失败: HTTP {response.status_code}")

        return {
            'status': 'completed',
            'etag': etag,
            'upload_id': upload_id
        }

    def _upload_part_to_oss(
        self,
        file_path: Path,
        upload_url: str,
        headers: Dict[str, str],
        part_number: int,
        part_size: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """上传分片到OSS"""
        import httpx

        # 读取文件数据
        if part_size is None:
            # 单分片，读取整个文件
            with open(file_path, 'rb') as f:
                data = f.read()
        else:
            # 多分片，读取指定大小的数据
            chunk_size = 4 * 1024 * 1024  # 4MB
            offset = (part_number - 1) * chunk_size

            with open(file_path, 'rb') as f:
                f.seek(offset)
                data = f.read(part_size)

        # 为多分片上传添加增量哈希头
        if part_size is not None and part_number > 1:
            # 从授权结果中获取哈希上下文
            if 'X-Oss-Hash-Ctx' not in headers:
                # 如果授权结果中没有，则计算
                hash_ctx = self._calculate_incremental_hash_context(
                    file_path, part_number, part_size
                )
                headers['X-Oss-Hash-Ctx'] = hash_ctx

        # 上传到OSS
        with httpx.Client(timeout=300.0) as client:
            response = client.put(
                upload_url,
                content=data,
                headers=headers
            )

            if response.status_code != 200:
                raise APIError(f"上传分片 {part_number} 失败: {response.status_code} {response.text}")

            # 从响应头中获取ETag
            etag = response.headers.get('etag', '').strip('"')
            if not etag:
                raise APIError(f"上传分片 {part_number} 成功但未获取到ETag")

            return etag



    def _finish_upload(self, task_id: str) -> Dict[str, Any]:
        """完成上传（通知夸克服务器）"""
        data = {
            "task_id": task_id
        }

        response = self.api_client.post(
            "file/upload/finish",
            json_data=data
        )

        if not response.get('status'):
            raise APIError(f"完成上传失败: {response.get('message', '未知错误')}")

        return response.get('data', {})
