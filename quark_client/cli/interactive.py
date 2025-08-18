"""
交互式CLI模式
"""

import os
import sys
import shlex
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel

from .utils import print_info, print_error, print_success, print_warning, get_client

from .commands.search import do_search
from .commands.download import download_file as cmd_download_file
from .commands.basic_fileops import create_folder, delete_files, rename_file

console = Console()


class InteractiveShell:
    """交互式Shell"""
    
    def __init__(self):
        self.client = None
        self.current_folder_id = "0"
        self.current_folder_name = "根目录"
        self.running = True

        # 目录栈：存储 (folder_id, folder_name) 的路径
        self.directory_stack = [("0", "根目录")]
        
        # 命令映射
        self.commands = {
            'help': self.cmd_help,
            'h': self.cmd_help,
            '?': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'q': self.cmd_exit,
            'ls': self.cmd_list,
            'list': self.cmd_list,
            'll': self.cmd_list_detailed,
            'cd': self.cmd_change_dir,
            'pwd': self.cmd_pwd,
            'search': self.cmd_search,
            'find': self.cmd_search,
            'download': self.cmd_download,
            'dl': self.cmd_download,
            'mkdir': self.cmd_mkdir,
            'rm': self.cmd_remove,
            'del': self.cmd_remove,
            'delete': self.cmd_remove,
            'rename': self.cmd_rename,
            'mv': self.cmd_rename,
            'info': self.cmd_info,
            'clear': self.cmd_clear,
            'cls': self.cmd_clear,
        }
    
    def start(self):
        """启动交互式模式"""
        console.print(Panel.fit(
            "[bold cyan]🌟 夸克网盘交互式CLI[/bold cyan]\n"
            "输入 'help' 查看可用命令\n"
            "输入 'exit' 退出程序",
            title="欢迎使用",
            border_style="cyan"
        ))
        
        # 检查登录状态
        try:
            self.client = get_client().__enter__()
            if not self.client.is_logged_in():
                print_error("未登录，请先使用 'quarkpan auth login' 登录")
                return
            
            print_success("✅ 已登录夸克网盘")
            print_info(f"当前位置: {self.current_folder_name}")
            
        except Exception as e:
            print_error(f"初始化失败: {e}")
            return
        
        # 主循环
        while self.running:
            try:
                # 显示提示符 - 使用友好显示名称
                display_name = self._get_display_name(self.current_folder_name)
                prompt = f"[cyan]quark[/cyan]:[blue]{display_name}[/blue]$ "
                command_line = Prompt.ask(prompt).strip()
                
                if not command_line:
                    continue
                
                # 解析命令
                try:
                    args = shlex.split(command_line)
                except ValueError as e:
                    print_error(f"命令解析错误: {e}")
                    continue
                
                if not args:
                    continue
                
                cmd = args[0].lower()
                cmd_args = args[1:]
                
                # 执行命令
                if cmd in self.commands:
                    try:
                        self.commands[cmd](cmd_args)
                    except KeyboardInterrupt:
                        print_info("\n命令被中断")
                    except Exception as e:
                        print_error(f"命令执行错误: {e}")
                else:
                    print_error(f"未知命令: {cmd}，输入 'help' 查看可用命令")
                    
            except KeyboardInterrupt:
                print_info("\n使用 'exit' 退出程序")
            except EOFError:
                break
        
        # 清理
        try:
            if self.client:
                self.client.__exit__(None, None, None)
        except:
            pass
        
        print_info("再见！")
    
    def cmd_help(self, args: List[str]):
        """显示帮助信息"""
        table = Table(title="可用命令", show_header=True, header_style="bold magenta")
        table.add_column("命令", style="cyan", width=15)
        table.add_column("别名", style="dim", width=10)
        table.add_column("说明", style="white")
        
        commands_help = [
            ("help", "h, ?", "显示此帮助信息"),
            ("exit", "quit, q", "退出程序"),
            ("ls", "list", "列出当前目录文件"),
            ("ll", "", "详细列出当前目录文件"),
            ("cd <path>", "", "切换目录"),
            ("cd ..", "", "返回上级目录"),
            ("cd", "", "返回根目录"),
            ("pwd", "", "显示当前目录和路径"),
            ("search <keyword>", "find", "搜索文件"),
            ("download <path>", "dl", "下载文件"),
            ("mkdir <name>", "", "创建文件夹"),
            ("rm <path>...", "del", "删除文件/文件夹"),
            ("rename <old> <new>", "mv", "重命名文件/文件夹"),
            ("info <path>", "", "显示文件信息"),
            ("clear", "cls", "清屏"),
        ]
        
        for cmd, alias, desc in commands_help:
            table.add_row(cmd, alias, desc)
        
        console.print(table)
        
        console.print("\n[bold yellow]路径说明:[/bold yellow]")
        console.print("• 使用文件名: [cyan]文件.txt[/cyan]")
        console.print("• 使用相对路径: [cyan]文件夹/文件.txt[/cyan]")
        console.print("• 使用绝对路径: [cyan]/文件夹/文件.txt[/cyan]")
        console.print("• 文件夹路径末尾加/: [cyan]文件夹/[/cyan]")
    
    def cmd_exit(self, args: List[str]):
        """退出程序"""
        self.running = False
    
    def cmd_list(self, args: List[str]):
        """列出文件"""
        try:
            # 模拟调用list命令
            files = self.client.list_files(self.current_folder_id, size=50)
            file_list = files.get('data', {}).get('list', [])

            if not file_list:
                print_info("目录为空")
                return

            # 显示当前目录信息 - 使用友好显示名称
            display_name = self._get_display_name(self.current_folder_name, max_length=50)
            print_info(f"当前目录: {display_name}")
            print_info(f"共 {len(file_list)} 个项目\n")

            for i, file_info in enumerate(file_list, 1):
                name = file_info.get('file_name', '未知')
                file_type = file_info.get('file_type', 1)

                if file_type == 0:  # 文件夹
                    console.print(f"  {i:2d}. 📁 {name}/")
                else:  # 文件
                    size = file_info.get('size', 0)
                    size_str = self._format_size(size)
                    console.print(f"  {i:2d}. 📄 {name} [dim]({size_str})[/dim]")

        except Exception as e:
            print_error(f"列出文件失败: {e}")
    
    def cmd_list_detailed(self, args: List[str]):
        """详细列出文件"""
        try:
            files = self.client.list_files(self.current_folder_id, size=50)
            file_list = files.get('data', {}).get('list', [])

            if not file_list:
                print_info("目录为空")
                return

            # 使用友好显示名称作为表格标题
            display_name = self._get_display_name(self.current_folder_name, max_length=30)
            table = Table(title=f"目录内容: {display_name}")
            table.add_column("序号", style="dim", width=4)
            table.add_column("类型", style="cyan", width=4)
            table.add_column("名称", style="white")
            table.add_column("大小", style="green", width=10)

            for i, file_info in enumerate(file_list, 1):
                name = file_info.get('file_name', '未知')
                file_type = file_info.get('file_type', 1)
                size = file_info.get('size', 0)

                if file_type == 0:
                    table.add_row(str(i), "📁", f"{name}/", "-")
                else:
                    size_str = self._format_size(size)
                    table.add_row(str(i), "📄", name, size_str)

            console.print(table)

        except Exception as e:
            print_error(f"列出文件失败: {e}")
    
    def cmd_change_dir(self, args: List[str]):
        """切换目录"""
        if not args:
            # 回到根目录
            self._change_to_root()
            return

        path = args[0]

        try:
            if path == "..":
                # 返回上级目录
                self._change_to_parent()
                return

            file_id, file_type = self.client.resolve_path(path, self.current_folder_id)

            if file_type != 'folder':
                print_error(f"'{path}' 不是文件夹")
                return

            # 获取文件夹的真实名称（优先使用列表缓存中的名称）
            real_name = self.client.get_real_file_name(file_id)
            if real_name:
                folder_name = real_name
            else:
                # 如果缓存中没有，则使用API获取的名称
                folder_info = self.client.get_file_info(file_id)
                folder_name = folder_info.get('file_name', path)

            # 切换到新目录
            self._change_to_directory(file_id, folder_name)

        except Exception as e:
            print_error(f"切换目录失败: {e}")
    
    def cmd_pwd(self, args: List[str]):
        """显示当前目录"""
        display_name = self._get_display_name(self.current_folder_name, max_length=50)
        current_path = self._get_current_path()

        print_info(f"当前目录: {display_name}")
        print_info(f"完整路径: {current_path}")
        if len(self.current_folder_name) > 50:
            print_info(f"完整名称: {self.current_folder_name}")
        print_info(f"目录ID: {self.current_folder_id}")
        print_info(f"目录层级: {len(self.directory_stack) - 1}")
    
    def cmd_search(self, args: List[str]):
        """搜索文件"""
        if not args:
            print_error("请提供搜索关键词")
            return
        
        keyword = " ".join(args)
        print_info(f"搜索: {keyword}")
        
        try:
            # 简化的搜索实现
            results = self.client.search_files(keyword, size=20)
            file_list = results.get('data', {}).get('list', [])
            total = results.get('metadata', {}).get('_total', len(file_list))
            
            if not file_list:
                print_warning("没有找到匹配的文件")
                return
            
            print_success(f"找到 {total} 个结果（显示前20个）:")
            
            for i, file_info in enumerate(file_list, 1):
                name = file_info.get('file_name', '未知')
                file_type = file_info.get('file_type', 1)
                size = file_info.get('size', 0)
                
                if file_type == 0:
                    console.print(f"  {i:2d}. 📁 {name}/")
                else:
                    size_str = self._format_size(size)
                    console.print(f"  {i:2d}. 📄 {name} [dim]({size_str})[/dim]")
                    
        except Exception as e:
            print_error(f"搜索失败: {e}")
    
    def cmd_download(self, args: List[str]):
        """下载文件"""
        if not args:
            print_error("请提供要下载的文件路径")
            return
        
        path = args[0]
        
        try:
            print_info(f"准备下载: {path}")
            
            def progress_callback(downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 100
                    print(f"\r下载进度: {percent:.1f}%", end="", flush=True)
            
            downloaded_path = self.client.download_file_by_name(
                path, 
                current_folder_id=self.current_folder_id,
                progress_callback=progress_callback
            )
            
            print()  # 换行
            print_success(f"✅ 下载完成: {downloaded_path}")
            
        except Exception as e:
            print()  # 换行
            print_error(f"下载失败: {e}")
    
    def cmd_mkdir(self, args: List[str]):
        """创建文件夹"""
        if not args:
            print_error("请提供文件夹名称")
            return
        
        folder_name = args[0]
        
        try:
            result = self.client.create_folder(folder_name, self.current_folder_id)
            
            if result and result.get('status') == 200:
                print_success(f"✅ 文件夹创建成功: {folder_name}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"创建文件夹失败: {error_msg}")
                
        except Exception as e:
            print_error(f"创建文件夹失败: {e}")
    
    def cmd_remove(self, args: List[str]):
        """删除文件"""
        if not args:
            print_error("请提供要删除的文件路径")
            return
        
        try:
            print_warning(f"准备删除 {len(args)} 个文件/文件夹:")
            
            for i, path in enumerate(args, 1):
                print_info(f"  {i}. {path}")
            
            from rich.prompt import Confirm
            if not Confirm.ask("\n确定要删除这些文件/文件夹吗？"):
                print_info("取消删除操作")
                return
            
            result = self.client.delete_files_by_name(args, self.current_folder_id)
            
            if result and result.get('status') == 200:
                print_success(f"✅ 成功删除 {len(args)} 个文件/文件夹")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"删除失败: {error_msg}")
                
        except Exception as e:
            print_error(f"删除失败: {e}")
    
    def cmd_rename(self, args: List[str]):
        """重命名文件"""
        if len(args) < 2:
            print_error("请提供原文件名和新文件名")
            return
        
        old_path = args[0]
        new_name = args[1]
        
        try:
            result = self.client.rename_file_by_name(old_path, new_name, self.current_folder_id)
            
            if result and result.get('status') == 200:
                print_success(f"✅ 重命名成功: {old_path} -> {new_name}")
            else:
                error_msg = result.get('message', '未知错误')
                print_error(f"重命名失败: {error_msg}")
                
        except Exception as e:
            print_error(f"重命名失败: {e}")
    
    def cmd_info(self, args: List[str]):
        """显示文件信息"""
        if not args:
            print_error("请提供文件路径")
            return
        
        path = args[0]
        
        try:
            file_info = self.client.get_file_info_by_name(path, self.current_folder_id)
            
            table = Table(title=f"文件信息: {path}")
            table.add_column("属性", style="cyan")
            table.add_column("值", style="white")
            
            table.add_row("文件名", file_info.get('file_name', '未知'))
            table.add_row("文件ID", file_info.get('fid', '未知'))
            table.add_row("类型", "文件夹" if file_info.get('file_type') == 0 else "文件")
            table.add_row("大小", self._format_size(file_info.get('size', 0)))
            table.add_row("格式", file_info.get('format_type', '未知'))
            
            console.print(table)
            
        except Exception as e:
            print_error(f"获取文件信息失败: {e}")
    
    def cmd_clear(self, args: List[str]):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _get_display_name(self, folder_name: str, max_length: int = 20) -> str:
        """
        获取友好显示的文件夹名称

        Args:
            folder_name: 原始文件夹名称
            max_length: 最大显示长度

        Returns:
            友好显示的名称
        """
        if not folder_name or folder_name == "根目录":
            return "根目录"

        # 如果名称不太长，直接返回
        if len(folder_name) <= max_length:
            return folder_name

        # 对于长名称，进行智能截断
        # 优先保留开头和结尾的重要信息
        if len(folder_name) > max_length:
            # 计算截断位置
            start_len = max_length // 2 - 1
            end_len = max_length - start_len - 3  # 3个字符用于"..."

            if start_len > 0 and end_len > 0:
                return f"{folder_name[:start_len]}...{folder_name[-end_len:]}"
            else:
                # 如果太短，直接截断
                return f"{folder_name[:max_length-3]}..."

        return folder_name


    def _change_to_root(self):
        """切换到根目录"""
        self.current_folder_id = "0"
        self.current_folder_name = "根目录"
        self.directory_stack = [("0", "根目录")]
        print_info("已切换到根目录")

    def _change_to_parent(self):
        """返回上级目录"""
        if len(self.directory_stack) <= 1:
            print_warning("已经在根目录，无法返回上级目录")
            return

        # 弹出当前目录，返回上级
        self.directory_stack.pop()
        parent_id, parent_name = self.directory_stack[-1]

        self.current_folder_id = parent_id
        self.current_folder_name = parent_name

        display_name = self._get_display_name(parent_name)
        print_success(f"已返回上级目录: {display_name}")

    def _change_to_directory(self, folder_id: str, folder_name: str):
        """切换到指定目录"""
        # 添加到目录栈
        self.directory_stack.append((folder_id, folder_name))

        # 更新当前目录
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name

        # 显示切换成功信息
        display_name = self._get_display_name(folder_name)
        print_success(f"已切换到: {display_name}")

    def _get_current_path(self) -> str:
        """获取当前路径字符串"""
        if len(self.directory_stack) <= 1:
            return "/"

        path_parts = []
        for _, name in self.directory_stack[1:]:  # 跳过根目录
            path_parts.append(name)

        return "/" + "/".join(path_parts)


def start_interactive():
    """启动交互式模式"""
    shell = InteractiveShell()
    shell.start()


if __name__ == "__main__":
    start_interactive()
