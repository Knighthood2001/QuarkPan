"""
分享相关命令
"""

from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from ..utils import (get_client, handle_api_error, print_error, print_info,
                     print_success, print_warning)


def create_share(
    file_paths: List[str],
    title: str = "",
    expire_days: int = 0,
    password: Optional[str] = None,
    use_id: bool = False
):
    """创建分享链接"""
    console = Console()

    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            # 解析文件路径或ID
            if use_id:
                file_ids = file_paths
                print_info(f"使用文件ID创建分享: {', '.join(file_ids)}")
            else:
                # 使用路径解析器将路径转换为ID
                from ...services.name_resolver import NameResolver
                resolver = NameResolver(client.files)

                file_ids = []
                for path in file_paths:
                    try:
                        file_id, _ = resolver.resolve_path(path)
                        file_ids.append(file_id)
                        print_info(f"解析路径 '{path}' -> {file_id}")
                    except Exception as e:
                        print_error(f"无法解析路径 '{path}': {e}")
                        raise typer.Exit(1)

            # 显示分享参数
            print_info("📤 创建分享链接...")
            if title:
                print_info(f"   标题: {title}")
            if expire_days > 0:
                print_info(f"   有效期: {expire_days} 天")
            else:
                print_info("   有效期: 永久")
            if password:
                print_info(f"   提取码: {password}")
            else:
                print_info("   提取码: 无")

            # 创建分享
            result = client.create_share(
                file_ids=file_ids,
                title=title,
                expire_days=expire_days,
                password=password
            )

            if result:
                print_success("✅ 分享创建成功!")

                # 显示分享信息
                table = Table(title="分享信息")
                table.add_column("属性", style="cyan")
                table.add_column("值", style="green")

                table.add_row("分享链接", result.get('share_url', 'N/A'))
                table.add_row("分享ID", result.get('pwd_id', 'N/A'))
                table.add_row("标题", result.get('title', 'N/A'))
                table.add_row("文件数量", str(result.get('file_num', 0)))

                if result.get('expired_type') == 1:
                    table.add_row("有效期", "永久")
                else:
                    expired_at = result.get('expired_at', 0)
                    if expired_at:
                        import datetime
                        expire_date = datetime.datetime.fromtimestamp(expired_at / 1000)
                        table.add_row("有效期", expire_date.strftime('%Y-%m-%d %H:%M:%S'))

                console.print(table)

                # 显示复制友好的格式
                share_url = result.get('share_url', '')
                if password:
                    print_info(f"\n📋 复制分享信息:")
                    print_info(f"链接: {share_url}")
                    print_info(f"提取码: {password}")
                else:
                    print_info(f"\n📋 分享链接: {share_url}")
            else:
                print_error("分享创建失败")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "创建分享")
        raise typer.Exit(1)


def list_my_shares(page: int = 1, size: int = 20):
    """列出我的分享"""
    console = Console()

    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"📋 获取我的分享列表 (第{page}页)...")

            result = client.get_my_shares(page=page, size=size)

            if result and result.get('status') == 200:
                data = result.get('data', {})
                shares = data.get('list', [])
                metadata = result.get('metadata', {})
                total = metadata.get('_total', 0)

                if not shares:
                    print_warning("暂无分享")
                    return

                print_success(f"✅ 找到 {total} 个分享")

                # 创建表格
                table = Table(title=f"我的分享 (第{page}页，共{total}个)")
                table.add_column("序号", style="cyan", width=4)
                table.add_column("标题", style="green", width=18)
                table.add_column("分享链接", style="bright_blue", width=35)
                table.add_column("类型", style="yellow", width=4)
                table.add_column("文件数", style="yellow", width=6)
                table.add_column("创建时间", style="blue", width=12)
                table.add_column("状态", style="magenta", width=6)
                table.add_column("访问量", style="dim", width=6)

                for i, share in enumerate(shares, 1):
                    # 格式化创建时间
                    created_at = share.get('created_at', 0)
                    if created_at:
                        import datetime
                        create_time = datetime.datetime.fromtimestamp(created_at / 1000)
                        time_str = create_time.strftime('%m-%d %H:%M')
                    else:
                        time_str = "未知"

                    # 状态
                    status = "正常" if share.get('status') == 1 else "已失效"

                    # 类型（文件夹或文件）
                    first_file = share.get('first_file', {})
                    is_dir = first_file.get('dir', False)
                    file_type = "📁" if is_dir else "📄"

                    # 分享链接（完整显示）
                    share_url = share.get('share_url', '')

                    # 访问量
                    click_pv = share.get('click_pv', 0)

                    table.add_row(
                        str(i),
                        share.get('title', '无标题')[:16],  # 稍微缩短标题
                        share_url,  # 完整显示分享链接
                        file_type,
                        str(share.get('file_num', 0)),
                        time_str,
                        status,
                        str(click_pv)
                    )

                console.print(table)

                # 显示详细统计信息
                print_info(f"\n📊 统计信息:")
                total_clicks = sum(share.get('click_pv', 0) for share in shares)
                total_saves = sum(share.get('save_pv', 0) for share in shares)
                total_downloads = sum(share.get('download_pv', 0) for share in shares)
                print_info(f"   总访问量: {total_clicks}")
                print_info(f"   总保存量: {total_saves}")
                print_info(f"   总下载量: {total_downloads}")

                # 分页信息
                total_pages = (total + size - 1) // size
                if total_pages > 1:
                    print_info(f"\n📄 第 {page}/{total_pages} 页")
                    if page < total_pages:
                        print_info(f"使用 'quarkpan shares --page {page + 1}' 查看下一页")
            else:
                print_error("获取分享列表失败")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "获取分享列表")
        raise typer.Exit(1)


def save_share(
    share_url: str,
    target_folder: str = "/",
    create_folder: bool = True
):
    """转存分享文件"""
    try:
        with get_client() as client:
            if not client.is_logged_in():
                print_error("未登录，请先使用 quarkpan auth login 登录")
                raise typer.Exit(1)

            print_info(f"🔗 解析分享链接: {share_url}")

            # 解析目标文件夹
            target_folder_id = "0"  # 默认根目录
            target_folder_name = None

            if target_folder != "/":
                # 解析目标文件夹路径
                from ...services.name_resolver import NameResolver
                resolver = NameResolver(client.files)

                try:
                    target_folder_id, _ = resolver.resolve_path(target_folder)
                    print_info(f"目标文件夹: {target_folder}")
                except:
                    if create_folder:
                        # 自动创建文件夹
                        target_folder_name = target_folder.split('/')[-1]
                        print_info(f"将创建新文件夹: {target_folder_name}")
                    else:
                        print_error(f"目标文件夹不存在: {target_folder}")
                        print_info("使用 --create-folder 自动创建文件夹")
                        raise typer.Exit(1)

            print_info("📥 开始转存...")

            result = client.save_shared_files(
                share_url=share_url,
                target_folder_id=target_folder_id,
                target_folder_name=target_folder_name
            )

            if result:
                share_info = result.get('share_info', {})
                file_count = share_info.get('file_count', 0)
                print_success(f"✅ 转存成功! 共转存 {file_count} 个文件")

                # 显示转存的文件信息
                files = share_info.get('files', [])
                if files and len(files) <= 10:  # 只显示前10个文件
                    print_info("\n📁 转存的文件:")
                    for file_info in files:
                        file_name = file_info.get('file_name', '未知文件')
                        file_size = file_info.get('size', 0)
                        if file_size > 0:
                            size_str = _format_size(file_size)
                            print_info(f"  📄 {file_name} ({size_str})")
                        else:
                            print_info(f"  📁 {file_name}")
            else:
                print_error("转存失败")
                raise typer.Exit(1)

    except Exception as e:
        handle_api_error(e, "转存分享")
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
