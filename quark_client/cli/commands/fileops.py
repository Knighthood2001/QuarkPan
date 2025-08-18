"""
文件操作命令模块
"""

import os
import typer
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from ..utils import print_info, print_error, print_success, print_warning, get_client, handle_api_error

console = Console()
fileops_app = typer.Typer(help="📁 文件操作")


@fileops_app.command("mkdir")
def create_folder(
    folder_name: str = typer.Argument(..., help="文件夹名称"),
    parent_id: str = typer.Option("0", "--parent", "-p", help="父文件夹ID，默认为根目录")
):
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


@fileops_app.command("rm")
def delete_files(
    paths: List[str] = typer.Argument(..., help="要删除的文件/文件夹路径或ID列表"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不询问确认"),
    use_id: bool = typer.Option(False, "--id", help="使用文件ID而不是路径")
):
    """删除文件或文件夹（支持文件名和ID）"""
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


@fileops_app.command("mv")
def move_files(
    file_ids: List[str] = typer.Argument(..., help="要移动的文件/文件夹ID列表"),
    target_folder_id: str = typer.Option(..., "--target", "-t", help="目标文件夹ID")
):
    """移动文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 显示要移动的文件信息
            print_info(f"准备移动 {len(file_ids)} 个文件/文件夹:")
            
            for i, file_id in enumerate(file_ids, 1):
                try:
                    file_info = client.get_file_info(file_id)
                    file_name = file_info.get('file_name', file_id)
                    file_type = "文件夹" if file_info.get('file_type') == 0 else "文件"
                    print_info(f"  {i}. {file_type}: {file_name}")
                except:
                    print_info(f"  {i}. ID: {file_id}")
            
            # 显示目标文件夹信息
            try:
                if target_folder_id == "0":
                    print_info("目标位置: 根目录")
                else:
                    target_info = client.get_file_info(target_folder_id)
                    target_name = target_info.get('file_name', target_folder_id)
                    print_info(f"目标文件夹: {target_name}")
            except:
                print_info(f"目标文件夹ID: {target_folder_id}")
            
            print_info("正在移动文件...")
            
            # 注意：移动功能目前可能存在API兼容性问题
            try:
                result = client.move_files(file_ids, target_folder_id)

                if result and result.get('status') == 200:
                    print_success(f"✅ 成功移动 {len(file_ids)} 个文件/文件夹")
                else:
                    error_msg = result.get('message', '未知错误')
                    print_error(f"移动失败: {error_msg}")
                    raise typer.Exit(1)
            except Exception as api_error:
                print_error("移动功能暂时不可用，可能是API兼容性问题")
                print_warning("建议使用以下替代方案：")
                print_info("1. 下载文件到本地，然后重新上传到目标文件夹")
                print_info("2. 使用网页版夸克网盘进行移动操作")
                raise typer.Exit(1)
            
    except Exception as e:
        handle_api_error(e, "移动文件")
        raise typer.Exit(1)


@fileops_app.command("rename")
def rename_file(
    path: str = typer.Argument(..., help="要重命名的文件/文件夹路径或ID"),
    new_name: str = typer.Argument(..., help="新名称"),
    use_id: bool = typer.Option(False, "--id", help="使用文件ID而不是路径")
):
    """重命名文件或文件夹（支持文件名和ID）"""
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


@fileops_app.command("info")
def show_fileops_info():
    """显示文件操作相关信息"""
    console.print("""
[bold cyan]📁 夸克网盘文件操作说明[/bold cyan]

[bold]创建文件夹:[/bold]
  quarkpan fileops mkdir <folder_name>        - 在根目录创建文件夹
  quarkpan fileops mkdir <folder_name> -p <parent_id>  - 在指定目录创建文件夹

[bold]删除文件/文件夹:[/bold]
  quarkpan fileops rm <file_id>...            - 删除文件/文件夹
  quarkpan fileops rm <file_id>... --force    - 强制删除，不询问确认

[bold]移动文件/文件夹:[/bold]
  quarkpan fileops mv <file_id>... -t <target_folder_id>  - 移动到指定文件夹

[bold]重命名文件/文件夹:[/bold]
  quarkpan fileops rename <file_id> <new_name>  - 重命名文件/文件夹

[bold]示例:[/bold]
  # 创建文件夹
  quarkpan fileops mkdir "我的文档"
  
  # 删除文件
  quarkpan fileops rm file_id1 file_id2
  
  # 移动文件到指定文件夹
  quarkpan fileops mv file_id1 file_id2 -t folder_id
  
  # 重命名文件
  quarkpan fileops rename file_id "新文件名.pdf"

[bold yellow]注意事项:[/bold yellow]
  • 需要先登录夸克网盘账号
  • 删除操作不可恢复，请谨慎操作
  • 移动文件时，目标文件夹必须存在
  • 重命名时，新名称不能与同目录下其他文件重名
  • 文件夹ID可以通过 quarkpan files list 命令获取

[bold]功能特点:[/bold]
  • ✅ 支持批量操作
  • ✅ 操作前显示文件信息
  • ✅ 删除前确认提示
  • ✅ 详细的错误信息
  • ✅ 支持文件和文件夹操作
""")


if __name__ == "__main__":
    fileops_app()
