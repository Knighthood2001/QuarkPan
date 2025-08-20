"""
下载命令模块
"""

import os
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from ..utils import (format_file_size, get_client, handle_api_error,
                     print_error, print_info, print_success, print_warning)

console = Console()
download_app = typer.Typer(help="📥 文件下载")


@download_app.command("file")
def download_file(
    file_id: str = typer.Argument(..., help="文件ID"),
    output_dir: str = typer.Option("downloads", "--output", "-o", help="下载目录"),
    filename: Optional[str] = typer.Option(None, "--name", "-n", help="自定义文件名")
):
    """下载单个文件"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在下载文件...")

            # 创建下载目录
            os.makedirs(output_dir, exist_ok=True)

            # 确定保存路径
            save_path = output_dir
            if filename:
                save_path = os.path.join(output_dir, filename)

            # 进度回调函数
            def progress_callback(downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 100
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    print(f"\r下载进度: {percent:.1f}% ({downloaded_mb:.1f}MB/{total_mb:.1f}MB)", end="", flush=True)
                else:
                    downloaded_mb = downloaded / (1024 * 1024)
                    print(f"\r已下载: {downloaded_mb:.1f}MB", end="", flush=True)

            # 下载文件
            downloaded_path = client.download_file(
                file_id,
                save_path,
                progress_callback=progress_callback
            )

            print()  # 换行
            print_success(f"✅ 文件下载成功: {downloaded_path}")

            # 显示文件信息
            if os.path.exists(downloaded_path):
                file_size = os.path.getsize(downloaded_path)
                print_info(f"文件大小: {format_file_size(file_size)}")

    except Exception as e:
        print()  # 换行
        handle_api_error(e, "下载文件")
        raise typer.Exit(1)


@download_app.command("files")
def download_files(
    file_ids: List[str] = typer.Argument(..., help="文件ID列表"),
    output_dir: str = typer.Option("downloads", "--output", "-o", help="下载目录")
):
    """批量下载文件"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在下载 {len(file_ids)} 个文件...")

            # 创建下载目录
            os.makedirs(output_dir, exist_ok=True)

            # 批量下载进度回调
            def batch_progress_callback(current_file, total_files, downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 100
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    print(
                        f"\r文件 {current_file}/{total_files}: {percent:.1f}% ({downloaded_mb:.1f}MB/{total_mb:.1f}MB)",
                        end="", flush=True)
                else:
                    downloaded_mb = downloaded / (1024 * 1024)
                    print(f"\r文件 {current_file}/{total_files}: {downloaded_mb:.1f}MB", end="", flush=True)

            # 批量下载文件
            downloaded_files = client.download_files(
                file_ids,
                output_dir,
                progress_callback=batch_progress_callback
            )

            print()  # 换行
            print_success(f"✅ 批量下载完成！成功下载 {len(downloaded_files)} 个文件")

            # 显示下载的文件列表
            if downloaded_files:
                table = Table(title="下载的文件")
                table.add_column("序号", style="dim", width=4)
                table.add_column("文件名", style="white")
                table.add_column("大小", style="green", width=12)

                for i, file_path in enumerate(downloaded_files, 1):
                    file_name = os.path.basename(file_path)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        size_str = format_file_size(file_size)
                    else:
                        size_str = "未知"

                    table.add_row(str(i), file_name, size_str)

                console.print(table)

    except Exception as e:
        print()  # 换行
        handle_api_error(e, "批量下载文件")
        raise typer.Exit(1)


@download_app.command("folder")
def download_folder(
    folder_id: str = typer.Argument(..., help="文件夹ID"),
    output_dir: str = typer.Option("downloads", "--output", "-o", help="下载目录"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r", help="递归下载子文件夹")
):
    """下载文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"正在获取文件夹内容...")

            # 获取文件夹信息
            try:
                folder_info = client.get_file_info(folder_id)
                folder_name = folder_info.get('file_name', f'folder_{folder_id}')
            except:
                folder_name = f'folder_{folder_id}'

            print_info(f"文件夹: {folder_name}")

            # 创建下载目录
            download_path = os.path.join(output_dir, folder_name)
            os.makedirs(download_path, exist_ok=True)

            # 获取文件夹内容
            def download_folder_recursive(fid, path):
                files = client.list_files(fid, size=1000)  # 获取大量文件
                file_list = files.get('data', {}).get('list', [])

                downloaded_files = []

                for file_info in file_list:
                    file_id = file_info.get('fid', '')
                    file_name = file_info.get('file_name', '')
                    file_type = file_info.get('file_type', 1)

                    if file_type == 0:  # 文件夹
                        if recursive:
                            print_info(f"进入文件夹: {file_name}")
                            sub_path = os.path.join(path, file_name)
                            os.makedirs(sub_path, exist_ok=True)
                            sub_files = download_folder_recursive(file_id, sub_path)
                            downloaded_files.extend(sub_files)
                    else:  # 文件
                        try:
                            print_info(f"下载文件: {file_name}")

                            def progress_callback(downloaded, total):
                                if total > 0:
                                    percent = (downloaded / total) * 100
                                    print(f"\r  进度: {percent:.1f}%", end="", flush=True)

                            file_path = client.download_file(
                                file_id,
                                path,
                                progress_callback=progress_callback
                            )
                            print()  # 换行
                            downloaded_files.append(file_path)

                        except Exception as e:
                            print()
                            print_warning(f"下载文件 {file_name} 失败: {e}")

                return downloaded_files

            # 开始递归下载
            downloaded_files = download_folder_recursive(folder_id, download_path)

            print_success(f"✅ 文件夹下载完成！成功下载 {len(downloaded_files)} 个文件")
            print_info(f"下载位置: {download_path}")

    except Exception as e:
        handle_api_error(e, "下载文件夹")
        raise typer.Exit(1)


@download_app.command("info")
def show_download_info():
    """显示下载相关信息"""
    console.print("""
[bold cyan]📥 夸克网盘下载说明[/bold cyan]

[bold]下载文件:[/bold]
  quarkpan download file <file_id>     - 下载单个文件
  quarkpan download files <file_id>... - 批量下载文件
  quarkpan download folder <folder_id> - 下载文件夹

[bold]使用方法:[/bold]
  1. [bold green]直接下载到本地[/bold green]
  2. 支持单文件、批量文件、整个文件夹下载
  3. 自动创建下载目录和保持文件夹结构

[bold]示例:[/bold]
  # 下载单个文件
  quarkpan download file 0d51b7344d894d20a671a5c567383749

  # 下载到指定目录
  quarkpan download file 0d51b7344d894d20a671a5c567383749 -o /path/to/downloads

  # 批量下载文件
  quarkpan download files file_id1 file_id2 file_id3

  # 下载整个文件夹
  quarkpan download folder folder_id

[bold yellow]注意事项:[/bold yellow]
  • 需要先登录夸克网盘账号
  • 下载速度取决于网络和夸克网盘限制
  • 大文件下载会显示进度条
  • 下载失败的文件会跳过并继续下载其他文件
  • 文件夹下载会保持原有的目录结构

[bold]功能特点:[/bold]
  • ✅ 直接下载，无需浏览器
  • ✅ 支持进度显示
  • ✅ 支持批量下载
  • ✅ 支持文件夹递归下载
  • ✅ 自动重试机制
""")


if __name__ == "__main__":
    download_app()
