"""
批量分享服务
"""

import csv
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core.api_client import QuarkAPIClient
from ..exceptions import APIError
from ..utils.logger import get_logger
from .file_service import FileService
from .share_service import ShareService


class BatchShareService:
    """批量分享服务"""

    def __init__(self, client: QuarkAPIClient):
        """
        初始化批量分享服务

        Args:
            client: API客户端实例
        """
        self.client = client
        self.file_service = FileService(client)
        self.share_service = ShareService(client)
        self.logger = get_logger(__name__)

    def collect_target_directories(self, exclude_patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        收集所有需要分享的目标目录（四级目录）

        Args:
            exclude_patterns: 排除的目录名称模式列表

        Returns:
            目标目录列表，每个元素包含目录信息和完整路径
        """
        if exclude_patterns is None:
            exclude_patterns = ["来自：分享"]

        target_directories = []

        self.logger.info("开始收集目标目录...")

        # 第一级：获取根目录下的所有文件夹（二级目录）
        try:
            root_response = self.file_service.list_files(folder_id="0", size=200)
            if not root_response.get('status') == 200:
                raise APIError("无法获取根目录文件列表")

            second_level_dirs = []
            root_files = root_response.get('data', {}).get('list', [])

            for item in root_files:
                if item.get('dir', False):  # 只处理文件夹
                    dir_name = item.get('file_name', '')
                    # 检查是否需要排除
                    if not any(pattern in dir_name for pattern in exclude_patterns):
                        second_level_dirs.append({
                            'fid': item.get('fid'),
                            'name': dir_name,
                            'path': f"/{dir_name}"
                        })
                        self.logger.info(f"找到二级目录: {dir_name}")
                    else:
                        self.logger.info(f"跳过排除目录: {dir_name}")

            # 第二级：遍历每个二级目录，获取三级目录
            for second_dir in second_level_dirs:
                try:
                    second_response = self.file_service.list_files(
                        folder_id=second_dir['fid'],
                        size=200
                    )
                    if not second_response.get('status') == 200:
                        self.logger.warning(f"无法获取二级目录文件列表: {second_dir['name']}")
                        continue

                    third_level_dirs = []
                    second_files = second_response.get('data', {}).get('list', [])

                    for item in second_files:
                        if item.get('dir', False):  # 只处理文件夹
                            dir_name = item.get('file_name', '')
                            third_level_dirs.append({
                                'fid': item.get('fid'),
                                'name': dir_name,
                                'path': f"{second_dir['path']}/{dir_name}"
                            })
                            self.logger.info(f"找到三级目录: {second_dir['name']}/{dir_name}")

                    # 第三级：遍历每个三级目录，获取四级目录（目标目录）
                    for third_dir in third_level_dirs:
                        try:
                            third_response = self.file_service.list_files(
                                folder_id=third_dir['fid'],
                                size=200
                            )
                            if not third_response.get('status') == 200:
                                self.logger.warning(f"无法获取三级目录文件列表: {third_dir['name']}")
                                continue

                            third_files = third_response.get('data', {}).get('list', [])

                            for item in third_files:
                                if item.get('dir', False):  # 只处理文件夹（目标目录）
                                    target_name = item.get('file_name', '')
                                    target_path = f"{third_dir['path']}/{target_name}"

                                    target_info = {
                                        'fid': item.get('fid'),
                                        'name': target_name,
                                        'full_path': target_path,
                                        'second_level': second_dir['name'],
                                        'third_level': third_dir['name'],
                                        'file_info': item
                                    }

                                    target_directories.append(target_info)
                                    self.logger.info(f"找到目标目录: {target_path}")

                        except Exception as e:
                            self.logger.error(f"处理三级目录时出错 {third_dir['name']}: {e}")
                            continue

                except Exception as e:
                    self.logger.error(f"处理二级目录时出错 {second_dir['name']}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"获取根目录时出错: {e}")
            raise

        self.logger.info(f"总共找到 {len(target_directories)} 个目标目录")
        return target_directories

    def create_batch_shares(self, target_directories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量创建分享链接

        Args:
            target_directories: 目标目录列表

        Returns:
            分享结果列表
        """
        share_results = []
        total = len(target_directories)

        self.logger.info(f"开始批量创建分享，共 {total} 个目录")

        for i, target_dir in enumerate(target_directories, 1):
            try:
                self.logger.info(f"正在创建分享 ({i}/{total}): {target_dir['full_path']}")

                # 创建分享
                share_result = self.share_service.create_share(
                    file_ids=[target_dir['fid']],
                    title=target_dir['name'],  # 使用目录名作为分享标题
                    expire_days=0,  # 永久
                    password=None   # 无密码
                )

                if share_result:
                    # 添加额外信息到结果中
                    share_info = {
                        'target_directory': target_dir,
                        'share_result': share_result,
                        'share_title': target_dir['name'],
                        'share_url': share_result.get('share_url', ''),
                        'share_id': share_result.get('pwd_id', ''),
                        'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'success': True
                    }
                    share_results.append(share_info)
                    self.logger.info(f"分享创建成功: {target_dir['name']} -> {share_result.get('share_url', '')}")
                else:
                    # 分享失败
                    share_info = {
                        'target_directory': target_dir,
                        'share_result': None,
                        'share_title': target_dir['name'],
                        'share_url': '',
                        'share_id': '',
                        'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'success': False,
                        'error': '分享创建失败'
                    }
                    share_results.append(share_info)
                    self.logger.error(f"分享创建失败: {target_dir['name']}")

            except Exception as e:
                # 记录错误并继续
                share_info = {
                    'target_directory': target_dir,
                    'share_result': None,
                    'share_title': target_dir['name'],
                    'share_url': '',
                    'share_id': '',
                    'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'success': False,
                    'error': str(e)
                }
                share_results.append(share_info)
                self.logger.error(f"创建分享时出错 {target_dir['name']}: {e}")

        successful = sum(1 for result in share_results if result['success'])
        self.logger.info(f"批量分享完成: 成功 {successful}/{total}")

        return share_results

    def export_to_csv(self, share_results: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        导出分享结果到CSV文件

        Args:
            share_results: 分享结果列表
            filename: CSV文件名，如果不指定则自动生成

        Returns:
            CSV文件路径
        """
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f"shares_{today}.csv"

        # 确保文件名以.csv结尾
        if not filename.endswith('.csv'):
            filename += '.csv'

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # 写入标题行
                headers = ['分享标题', '分享链接', '完整路径', '创建时间']
                writer.writerow(headers)

                # 写入数据行
                for result in share_results:
                    if result['success']:
                        row = [
                            result['share_title'],
                            result['share_url'],
                            result['target_directory']['full_path'],
                            result['created_time']
                        ]
                        writer.writerow(row)
                    else:
                        # 对于失败的分享，也记录到CSV中，但链接为空
                        row = [
                            result['share_title'],
                            f"创建失败: {result.get('error', '未知错误')}",
                            result['target_directory']['full_path'],
                            result['created_time']
                        ]
                        writer.writerow(row)

            self.logger.info(f"CSV文件已保存: {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"保存CSV文件时出错: {e}")
            raise

    def batch_share_and_export(self, csv_filename: Optional[str] = None, exclude_patterns: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], str]:
        """
        一站式批量分享和导出服务

        Args:
            csv_filename: CSV文件名
            exclude_patterns: 排除的目录名称模式列表

        Returns:
            (分享结果列表, CSV文件路径)
        """
        # 1. 收集目标目录
        self.logger.info("🔍 开始收集目标目录...")
        target_directories = self.collect_target_directories(exclude_patterns)

        if not target_directories:
            self.logger.warning("没有找到任何目标目录")
            return [], ""

        # 2. 批量创建分享
        self.logger.info("📤 开始批量创建分享...")
        share_results = self.create_batch_shares(target_directories)

        # 3. 导出到CSV
        self.logger.info("📊 开始导出CSV文件...")
        csv_path = self.export_to_csv(share_results, csv_filename)

        # 4. 统计信息
        successful = sum(1 for result in share_results if result['success'])
        failed = len(share_results) - successful

        self.logger.info(f"✅ 批量分享完成!")
        self.logger.info(f"   总计: {len(share_results)} 个目录")
        self.logger.info(f"   成功: {successful} 个")
        self.logger.info(f"   失败: {failed} 个")
        self.logger.info(f"   CSV文件: {csv_path}")

        return share_results, csv_path
