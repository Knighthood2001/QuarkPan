"""
文件管理命令
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional, List

from ..utils import (
    get_client, format_file_size, format_timestamp,
    print_error, print_success, print_warning, print_info,
    confirm_action, handle_api_error, validate_file_id,
    truncate_text, get_file_type_icon, FolderNavigator,
    get_folder_name_by_id, select_folder_from_list
)

files_app = typer.Typer(help="📁 文件管理")
console = Console()


@files_app.command("list")
def list_files(
    folder_id: str = typer.Argument("0", help="文件夹ID，默认为根目录"),
    page: int = typer.Option(1, "--page", "-p", help="页码"),
    size: int = typer.Option(20, "--size", "-s", help="每页数量"),
    sort_field: str = typer.Option("file_name", "--sort", help="排序字段 (file_name, size, updated_at)"),
    sort_order: str = typer.Option("asc", "--order", help="排序方向 (asc/desc)"),
    show_details: bool = typer.Option(False, "--details", "-d", help="显示详细信息"),
    folders_only: bool = typer.Option(False, "--folders-only", help="只显示文件夹"),
    files_only: bool = typer.Option(False, "--files-only", help="只显示文件")
):
    """列出文件和文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 验证文件夹ID
            if folder_id != "0" and not validate_file_id(folder_id):
                print_error("无效的文件夹ID格式")
                raise typer.Exit(1)
            
            # 获取文件列表
            if folders_only or files_only:
                files = client.list_files_with_details(
                    folder_id=folder_id,
                    page=page,
                    size=size,
                    sort_field=sort_field,
                    sort_order=sort_order,
                    include_folders=not files_only,
                    include_files=not folders_only
                )
            else:
                files = client.list_files(
                    folder_id=folder_id,
                    page=page,
                    size=size,
                    sort_field=sort_field,
                    sort_order=sort_order
                )
            
            if not files or 'data' not in files:
                print_error("无法获取文件列表")
                raise typer.Exit(1)
            
            file_list = files['data'].get('list', [])
            total = files['data'].get('total', 0)
            
            # 显示标题
            folder_name = "根目录" if folder_id == "0" else f"文件夹 {folder_id}"
            rprint(f"\n📂 [bold]{folder_name}[/bold]")
            
            if not file_list:
                print_warning("文件夹为空")
                return
            
            if show_details:
                # 详细表格视图
                table = Table(title=f"第{page}页，共{total}个项目")
                table.add_column("序号", style="dim", width=4)
                table.add_column("类型", style="cyan", width=4)
                table.add_column("名称", style="white", min_width=20)
                table.add_column("大小", style="green", width=10)
                table.add_column("修改时间", style="yellow", width=16)
                table.add_column("ID", style="dim", width=8)
                
                for i, file_info in enumerate(file_list, (page-1)*size + 1):
                    name = file_info.get('file_name', '未知')
                    size_bytes = file_info.get('size', 0)
                    file_type = file_info.get('file_type', 0)
                    updated_at = file_info.get('updated_at', '')
                    fid = file_info.get('fid', '')
                    
                    is_folder = file_type == 0
                    type_icon = get_file_type_icon(name, is_folder)
                    size_str = "-" if is_folder else format_file_size(size_bytes)
                    time_str = format_timestamp(updated_at) if updated_at else "-"
                    short_id = fid[:8] + "..." if len(fid) > 8 else fid
                    
                    table.add_row(
                        str(i), 
                        type_icon, 
                        truncate_text(name, 30), 
                        size_str, 
                        time_str,
                        short_id
                    )
                
                console.print(table)
            else:
                # 简洁列表视图
                rprint(f"[dim]第{page}页，共{total}个项目[/dim]\n")
                
                for i, file_info in enumerate(file_list, (page-1)*size + 1):
                    name = file_info.get('file_name', '未知')
                    file_type = file_info.get('file_type', 0)
                    is_folder = file_type == 0
                    type_icon = get_file_type_icon(name, is_folder)
                    
                    rprint(f"  {i:2d}. {type_icon} {name}")
            
            # 显示分页信息
            if total > size:
                total_pages = (total + size - 1) // size
                rprint(f"\n[dim]第 {page}/{total_pages} 页，共 {total} 个项目[/dim]")
                if page < total_pages:
                    rprint(f"[dim]使用 --page {page + 1} 查看下一页[/dim]")
                    
    except Exception as e:
        handle_api_error(e, "获取文件列表")
        raise typer.Exit(1)


@files_app.command("mkdir")
def create_folder(
    name: str = typer.Argument(..., help="文件夹名称"),
    parent_id: str = typer.Option("0", "--parent", "-p", help="父文件夹ID，默认为根目录")
):
    """创建文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 验证父文件夹ID
            if parent_id != "0" and not validate_file_id(parent_id):
                print_error("无效的父文件夹ID格式")
                raise typer.Exit(1)
            
            print_info(f"正在创建文件夹: {name}")
            
            result = client.files.create_folder(name, parent_id)
            
            if result:
                print_success(f"文件夹 '{name}' 创建成功")
                
                # 尝试获取新创建文件夹的ID
                if isinstance(result, dict) and 'data' in result:
                    folder_id = result['data'].get('fid')
                    if folder_id:
                        rprint(f"[dim]文件夹ID: {folder_id}[/dim]")
            else:
                print_error("创建文件夹失败")
                raise typer.Exit(1)
                
    except Exception as e:
        handle_api_error(e, "创建文件夹")
        raise typer.Exit(1)


@files_app.command("rm")
def delete_files(
    file_ids: List[str] = typer.Argument(..., help="要删除的文件/文件夹ID列表"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不询问确认")
):
    """删除文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 验证文件ID
            for file_id in file_ids:
                if not validate_file_id(file_id):
                    print_error(f"无效的文件ID格式: {file_id}")
                    raise typer.Exit(1)
            
            # 确认删除
            if not force:
                file_count = len(file_ids)
                if not confirm_action(f"确定要删除 {file_count} 个项目吗？此操作不可恢复"):
                    print_info("删除操作已取消")
                    return
            
            print_info(f"正在删除 {len(file_ids)} 个项目...")
            
            result = client.files.delete_files(file_ids)
            
            if result:
                print_success(f"成功删除 {len(file_ids)} 个项目")
            else:
                print_error("删除失败")
                raise typer.Exit(1)
                
    except Exception as e:
        handle_api_error(e, "删除文件")
        raise typer.Exit(1)


@files_app.command("mv")
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
            
            # 验证文件ID
            for file_id in file_ids:
                if not validate_file_id(file_id):
                    print_error(f"无效的文件ID格式: {file_id}")
                    raise typer.Exit(1)
            
            # 验证目标文件夹ID
            if not validate_file_id(target_folder_id):
                print_error("无效的目标文件夹ID格式")
                raise typer.Exit(1)
            
            print_info(f"正在移动 {len(file_ids)} 个项目到目标文件夹...")
            
            result = client.files.move_files(file_ids, target_folder_id)
            
            if result:
                print_success(f"成功移动 {len(file_ids)} 个项目")
            else:
                print_error("移动失败")
                raise typer.Exit(1)
                
    except Exception as e:
        handle_api_error(e, "移动文件")
        raise typer.Exit(1)


@files_app.command("rename")
def rename_file(
    file_id: str = typer.Argument(..., help="要重命名的文件/文件夹ID"),
    new_name: str = typer.Argument(..., help="新名称")
):
    """重命名文件或文件夹"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)
            
            # 验证文件ID
            if not validate_file_id(file_id):
                print_error("无效的文件ID格式")
                raise typer.Exit(1)
            
            print_info(f"正在重命名为: {new_name}")
            
            result = client.files.rename_file(file_id, new_name)
            
            if result:
                print_success(f"重命名成功: {new_name}")
            else:
                print_error("重命名失败")
                raise typer.Exit(1)
                
    except Exception as e:
        handle_api_error(e, "重命名文件")
        raise typer.Exit(1)


@files_app.command("info")
def file_info(
    file_id: str = typer.Argument(..., help="文件/文件夹ID")
):
    """获取文件详细信息"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            # 验证文件ID
            if not validate_file_id(file_id):
                print_error("无效的文件ID格式")
                raise typer.Exit(1)

            print_info("正在获取文件信息...")

            file_info = client.get_file_info(file_id)

            if file_info:
                # 创建信息表格
                table = Table(title="📄 文件信息")
                table.add_column("属性", style="cyan")
                table.add_column("值", style="white")

                name = file_info.get('file_name', '未知')
                size = file_info.get('size', 0)
                file_type = file_info.get('file_type', 0)
                created_at = file_info.get('created_at', '')
                updated_at = file_info.get('updated_at', '')
                fid = file_info.get('fid', '')

                is_folder = file_type == 0
                type_name = "文件夹" if is_folder else "文件"
                size_str = "-" if is_folder else format_file_size(size)

                table.add_row("ID", fid)
                table.add_row("名称", name)
                table.add_row("类型", type_name)
                table.add_row("大小", size_str)
                table.add_row("创建时间", format_timestamp(created_at) if created_at else "-")
                table.add_row("修改时间", format_timestamp(updated_at) if updated_at else "-")

                console.print(table)
            else:
                print_error("无法获取文件信息")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取文件信息")
        raise typer.Exit(1)


@files_app.command("download")
def get_download_url(
    file_id: str = typer.Argument(..., help="文件ID")
):
    """获取文件下载链接"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            # 验证文件ID
            if not validate_file_id(file_id):
                print_error("无效的文件ID格式")
                raise typer.Exit(1)

            print_info("正在获取下载链接...")

            download_url = client.get_download_url(file_id)

            if download_url:
                print_success("下载链接获取成功")
                rprint(f"[green]{download_url}[/green]")
                rprint("\n[dim]提示: 可以使用 wget、curl 或浏览器下载文件[/dim]")
            else:
                print_error("无法获取下载链接")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取下载链接")
        raise typer.Exit(1)


@files_app.command("pwd")
def show_folder_path(
    folder_id: str = typer.Argument("0", help="文件夹ID，默认为根目录")
):
    """显示文件夹路径信息"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            if folder_id == "0":
                rprint("📍 当前位置: [bold cyan]根目录[/bold cyan]")
                rprint("📂 文件夹ID: [dim]0[/dim]")
                return

            # 验证文件夹ID
            if not validate_file_id(folder_id):
                print_error("无效的文件夹ID格式")
                raise typer.Exit(1)

            # 获取文件夹信息
            try:
                file_info = client.get_file_info(folder_id)
                if file_info:
                    name = file_info.get('file_name', '未知')
                    file_type = file_info.get('file_type', 0)

                    if file_type != 0:
                        print_error("指定的ID不是文件夹")
                        raise typer.Exit(1)

                    rprint(f"📍 当前位置: [bold cyan]{name}[/bold cyan]")
                    rprint(f"📂 文件夹ID: [dim]{folder_id}[/dim]")

                    # 显示文件夹统计
                    files = client.list_files(folder_id=folder_id, size=1)
                    if files and 'data' in files:
                        total = files['data'].get('total', 0)
                        rprint(f"📊 包含项目: [green]{total}[/green] 个")
                else:
                    print_error("无法获取文件夹信息")
                    raise typer.Exit(1)
            except Exception as e:
                handle_api_error(e, "获取文件夹信息")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "显示文件夹路径")
        raise typer.Exit(1)


@files_app.command("browse")
def browse_folders():
    """交互式文件夹浏览"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            navigator = FolderNavigator()

            while True:
                current_folder_id, current_folder_name = navigator.get_current_folder()
                breadcrumb = navigator.get_breadcrumb()

                # 显示当前位置
                rprint(f"\n📍 当前位置: [bold cyan]{breadcrumb}[/bold cyan]")

                # 获取当前文件夹内容
                try:
                    files = client.list_files(folder_id=current_folder_id, size=50)

                    if not files or 'data' not in files:
                        print_error("无法获取文件列表")
                        break

                    file_list = files['data'].get('list', [])
                    total = files['data'].get('total', 0)

                    if not file_list:
                        print_warning("文件夹为空")
                        if navigator.can_go_back():
                            rprint("[dim]输入 'b' 返回上级目录，输入 'q' 退出[/dim]")
                            choice = console.input("[cyan]请选择: [/cyan]").strip().lower()
                            if choice == 'b':
                                navigator.go_back()
                                continue
                            elif choice == 'q':
                                break
                        else:
                            break
                        continue

                    # 显示文件列表
                    rprint(f"\n📂 [bold]{current_folder_name}[/bold] ({total} 个项目)")

                    folders = []
                    files_count = 0

                    for i, file_info in enumerate(file_list, 1):
                        name = file_info.get('file_name', '未知')
                        file_type = file_info.get('file_type', 0)
                        size = file_info.get('size', 0)
                        fid = file_info.get('fid', '')

                        is_folder = file_type == 0
                        type_icon = get_file_type_icon(name, is_folder)

                        if is_folder:
                            folders.append((i, fid, name))
                            rprint(f"  {i:2d}. {type_icon} [cyan]{name}[/cyan]")
                        else:
                            files_count += 1
                            size_str = format_file_size(size)
                            rprint(f"  {i:2d}. {type_icon} {name} [dim]({size_str})[/dim]")

                    # 显示统计信息
                    rprint(f"\n[dim]📁 {len(folders)} 个文件夹，📄 {files_count} 个文件[/dim]")

                    # 显示操作提示
                    if folders:
                        rprint("[dim]输入序号进入文件夹", end="")
                    if navigator.can_go_back():
                        rprint("[dim]，输入 'b' 返回上级", end="")
                    rprint("[dim]，输入 'q' 退出[/dim]")

                    # 获取用户选择
                    try:
                        choice = console.input("[cyan]请选择: [/cyan]").strip()

                        if choice.lower() == 'q':
                            break
                        elif choice.lower() == 'b' and navigator.can_go_back():
                            navigator.go_back()
                            continue
                        else:
                            # 尝试解析为序号
                            try:
                                seq = int(choice)
                                if 1 <= seq <= len(file_list):
                                    selected_file = file_list[seq - 1]
                                    if selected_file.get('file_type', 0) == 0:  # 是文件夹
                                        folder_id = selected_file.get('fid')
                                        folder_name = selected_file.get('file_name')
                                        navigator.enter_folder(folder_id, folder_name)
                                        continue
                                    else:
                                        print_info(f"这是一个文件: {selected_file.get('file_name')}")
                                        print_info(f"文件ID: {selected_file.get('fid')}")
                                        continue
                                else:
                                    print_error("无效的序号")
                                    continue
                            except ValueError:
                                print_error("无效的输入")
                                continue

                    except KeyboardInterrupt:
                        rprint("\n[yellow]⚠️ 退出浏览[/yellow]")
                        break

                except Exception as e:
                    handle_api_error(e, "获取文件列表")
                    break

            print_info("浏览结束")

    except Exception as e:
        handle_api_error(e, "文件浏览")
        raise typer.Exit(1)


@files_app.command("goto")
def goto_folder(
    target: str = typer.Argument(..., help="目标文件夹（可以是ID、名称或序号）"),
    parent_folder: str = typer.Option("0", "--parent", "-p", help="父文件夹ID，用于按名称或序号查找")
):
    """智能进入文件夹（支持ID、名称、序号）"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            folder_id = None
            folder_name = None

            # 1. 首先尝试作为文件夹ID
            if validate_file_id(target):
                try:
                    file_info = client.get_file_info(target)
                    if file_info and file_info.get('file_type', 0) == 0:
                        folder_id = target
                        folder_name = file_info.get('file_name', '未知')
                        print_info(f"通过ID找到文件夹: {folder_name}")
                except:
                    pass

            # 2. 如果不是有效ID，尝试作为序号或名称
            if not folder_id:
                # 获取父文件夹的内容
                files = client.list_files(folder_id=parent_folder, size=100)
                if not files or 'data' not in files:
                    print_error("无法获取父文件夹内容")
                    raise typer.Exit(1)

                file_list = files['data'].get('list', [])
                folders = [f for f in file_list if f.get('file_type', 0) == 0]

                if not folders:
                    print_error("父文件夹中没有子文件夹")
                    raise typer.Exit(1)

                # 尝试作为序号
                try:
                    seq = int(target)
                    if 1 <= seq <= len(folders):
                        folder_info = folders[seq - 1]
                        folder_id = folder_info.get('fid')
                        folder_name = folder_info.get('file_name')
                        print_info(f"通过序号找到文件夹: {folder_name}")
                    else:
                        print_error(f"序号超出范围 (1-{len(folders)})")
                        raise typer.Exit(1)
                except ValueError:
                    # 不是数字，尝试作为名称匹配
                    target_lower = target.lower()
                    matches = []

                    for folder_info in folders:
                        name = folder_info.get('file_name', '')
                        if target_lower in name.lower():
                            matches.append(folder_info)

                    if len(matches) == 1:
                        folder_info = matches[0]
                        folder_id = folder_info.get('fid')
                        folder_name = folder_info.get('file_name')
                        print_info(f"通过名称找到文件夹: {folder_name}")
                    elif len(matches) > 1:
                        print_warning(f"找到多个匹配的文件夹:")
                        for i, folder_info in enumerate(matches, 1):
                            name = folder_info.get('file_name', '')
                            rprint(f"  {i}. 📁 {name}")
                        print_error("请使用更精确的名称或使用序号")
                        raise typer.Exit(1)
                    else:
                        print_error(f"未找到名称包含 '{target}' 的文件夹")

                        # 显示可用的文件夹
                        rprint("\n[cyan]可用的文件夹:[/cyan]")
                        for i, folder_info in enumerate(folders, 1):
                            name = folder_info.get('file_name', '')
                            rprint(f"  {i}. 📁 {name}")
                        raise typer.Exit(1)

            # 3. 进入找到的文件夹
            if folder_id:
                rprint(f"\n📂 进入文件夹: [bold cyan]{folder_name}[/bold cyan]")

                # 列出文件夹内容
                files = client.list_files(folder_id=folder_id, size=20)
                if files and 'data' in files:
                    file_list = files['data'].get('list', [])
                    total = files['data'].get('total', 0)

                    rprint(f"📊 包含 {total} 个项目")

                    if file_list:
                        rprint("\n[dim]前20个项目:[/dim]")
                        for i, file_info in enumerate(file_list, 1):
                            name = file_info.get('file_name', '未知')
                            file_type = file_info.get('file_type', 0)
                            type_icon = get_file_type_icon(name, file_type == 0)
                            rprint(f"  {i:2d}. {type_icon} {name}")

                        if total > 20:
                            rprint(f"\n[dim]... 还有 {total - 20} 个项目[/dim]")
                    else:
                        rprint("[yellow]📂 文件夹为空[/yellow]")

                    rprint(f"\n[dim]💡 使用以下命令继续操作:[/dim]")
                    rprint(f"[dim]   quarkpan ls {folder_id} --details  # 详细列表[/dim]")
                    rprint(f"[dim]   quarkpan cd {folder_id}           # 进入此文件夹[/dim]")
                    rprint(f"[dim]   quarkpan files browse            # 交互式浏览[/dim]")
                else:
                    print_error("无法获取文件夹内容")
            else:
                print_error("未找到指定的文件夹")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "进入文件夹")
        raise typer.Exit(1)


if __name__ == "__main__":
    files_app()
