"""
基础文件操作命令
"""

import typer
from typing import List
from rich.prompt import Confirm

from ..utils import print_info, print_error, print_success, print_warning, get_client, handle_api_error


def create_folder(folder_name: str, parent_id: str = "0"):
    """创建文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            print_info(f"正在创建文件夹: {folder_name}")
            
            result = client.create_folder(folder_name, parent_id)
            
            if result and result.get('status') == 200:
                print_success(f"✅ 文件夹创建成功: {folder_name}")
                
                # 显示创建的文件夹信息
                if 'data' in result:
                    folder_info = result['data']
                    folder_id = folder_info.get('fid', '')
                    if folder_id:
                        print_info(f"文件夹ID: {folder_id}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"创建文件夹失败: {error_msg}")
                raise typer.Exit(1)
            
    except Exception as e:
        handle_api_error(e, "创建文件夹")
        raise typer.Exit(1)


def delete_files(paths: List[str], force: bool = False, use_id: bool = False):
    """删除文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 解析路径或使用ID
            if use_id:
                file_ids = paths
                # 显示要删除的文件信息
                print_warning(f"准备删除 {len(file_ids)} 个文件/文件夹:")
                
                for i, file_id in enumerate(file_ids, 1):
                    try:
                        file_info = client.get_file_info(file_id)
                        file_name = file_info.get('file_name', file_id)
                        file_type = "文件夹" if file_info.get('file_type') == 0 else "文件"
                        print_info(f"  {i}. {file_type}: {file_name}")
                    except:
                        print_info(f"  {i}. ID: {file_id}")
            else:
                # 使用路径解析
                print_warning(f"准备删除 {len(paths)} 个文件/文件夹:")
                
                resolved_items = []
                for i, path in enumerate(paths, 1):
                    try:
                        file_id, file_type = client.resolve_path(path)
                        file_info = client.get_file_info(file_id)
                        file_name = file_info.get('file_name', path)
                        type_name = "文件夹" if file_type == 'folder' else "文件"
                        print_info(f"  {i}. {type_name}: {file_name} (路径: {path})")
                        resolved_items.append(file_id)
                    except Exception as e:
                        print_error(f"  {i}. 无法解析路径 '{path}': {e}")
                        raise typer.Exit(1)
                
                file_ids = resolved_items
            
            # 确认删除
            if not force:
                if not Confirm.ask("\n确定要删除这些文件/文件夹吗？"):
                    print_info("取消删除操作")
                    return
            
            print_info("正在删除文件...")
            
            if use_id:
                result = client.delete_files(file_ids)
            else:
                result = client.delete_files_by_name(paths)
            
            if result and result.get('status') == 200:
                print_success(f"✅ 成功删除 {len(file_ids)} 个文件/文件夹")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"删除失败: {error_msg}")
                raise typer.Exit(1)
            
    except Exception as e:
        handle_api_error(e, "删除文件")
        raise typer.Exit(1)


def rename_file(path: str, new_name: str, use_id: bool = False):
    """重命名文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 解析路径或使用ID
            if use_id:
                file_id = path
                try:
                    file_info = client.get_file_info(file_id)
                    old_name = file_info.get('file_name', file_id)
                    file_type = "文件夹" if file_info.get('file_type') == 0 else "文件"
                    print_info(f"当前{file_type}名称: {old_name}")
                    print_info(f"新{file_type}名称: {new_name}")
                except:
                    print_info(f"文件ID: {file_id}")
                    print_info(f"新名称: {new_name}")
                
                result = client.rename_file(file_id, new_name)
            else:
                try:
                    file_id, file_type = client.resolve_path(path)
                    file_info = client.get_file_info(file_id)
                    old_name = file_info.get('file_name', path)
                    type_name = "文件夹" if file_type == 'folder' else "文件"
                    print_info(f"当前{type_name}名称: {old_name} (路径: {path})")
                    print_info(f"新{type_name}名称: {new_name}")
                except Exception as e:
                    print_error(f"无法解析路径 '{path}': {e}")
                    raise typer.Exit(1)
                
                result = client.rename_file_by_name(path, new_name)
            
            print_info("正在重命名...")
            
            if result and result.get('status') == 200:
                print_success(f"✅ 重命名成功: {new_name}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"重命名失败: {error_msg}")
                raise typer.Exit(1)
            
    except Exception as e:
        handle_api_error(e, "重命名文件")
        raise typer.Exit(1)


def file_info(file_id: str):
    """获取文件详细信息"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在获取文件信息: {file_id}")

            file_info = client.get_file_info(file_id)

            if file_info:
                from rich.table import Table
                from rich.console import Console

                console = Console()
                table = Table(title=f"文件信息")
                table.add_column("属性", style="cyan")
                table.add_column("值", style="white")

                table.add_row("文件名", file_info.get('file_name', '未知'))
                table.add_row("文件ID", file_info.get('fid', '未知'))
                table.add_row("类型", "文件夹" if file_info.get('file_type') == 0 else "文件")
                table.add_row("大小", _format_size(file_info.get('size', 0)))
                table.add_row("格式", file_info.get('format_type', '未知'))
                table.add_row("创建时间", file_info.get('created_at', '未知'))
                table.add_row("修改时间", file_info.get('updated_at', '未知'))

                console.print(table)
            else:
                print_error("无法获取文件信息")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取文件信息")
        raise typer.Exit(1)


def browse_folder(folder_id: str = "0"):
    """交互式文件夹浏览"""
    print_warning("交互式浏览功能正在开发中...")
    print_info("请使用 'quarkpan interactive' 启动完整的交互式模式")


def goto_folder(target: str, current_folder: str = "0"):
    """智能进入文件夹"""
    print_warning("智能导航功能正在开发中...")
    print_info("请使用 'quarkpan interactive' 启动完整的交互式模式")


def get_download_link(file_id: str):
    """获取文件下载链接"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在获取下载链接: {file_id}")

            download_url = client.get_download_url(file_id)

            if download_url:
                print_success("下载链接获取成功:")
                print_info(download_url)
            else:
                print_error("无法获取下载链接")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取下载链接")
        raise typer.Exit(1)


def _format_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
