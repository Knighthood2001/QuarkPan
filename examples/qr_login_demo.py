#!/usr/bin/env python3
"""
二维码登录演示
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from quark_client import QuarkClient


def demo_qr_login():
    """演示二维码登录"""
    print("🔲 夸克网盘二维码登录演示")
    print("=" * 50)
    
    print("📝 功能说明:")
    print("1. 自动打开无头浏览器访问夸克网盘")
    print("2. 自动提取登录二维码并保存为图片")
    print("3. 在终端显示二维码预览")
    print("4. 等待用户扫码登录")
    print("5. 自动检测登录状态并保存凭证")
    print()
    
    choice = input("是否开始二维码登录演示？(y/n): ").lower().strip()
    
    if choice != 'y':
        print("⏭️ 演示已取消")
        return
    
    try:
        print("\n🚀 开始二维码登录...")
        
        # 创建客户端，强制使用二维码登录
        with QuarkClient(auto_login=False) as client:
            # 检查当前登录状态
            if client.is_logged_in():
                print("✅ 检测到已有登录信息")
                choice = input("是否强制重新登录？(y/n): ").lower().strip()
                if choice != 'y':
                    print("✅ 使用现有登录信息")
                    test_api(client)
                    return
            
            # 执行二维码登录
            print("🔲 启动二维码登录流程...")
            cookies = client.login(force_relogin=True, use_qr=True)
            
            if cookies:
                print("✅ 二维码登录成功！")
                print(f"🍪 获取到 {len(cookies)} 字符的Cookie")
                
                # 测试API功能
                test_api(client)
                
            else:
                print("❌ 二维码登录失败")
                
    except KeyboardInterrupt:
        print("\n⏹️ 用户取消登录")
    except Exception as e:
        print(f"❌ 登录过程出错: {e}")
        import traceback
        traceback.print_exc()


def test_api(client):
    """测试API功能"""
    print("\n🧪 测试API功能...")
    
    try:
        # 获取文件列表
        print("📁 获取文件列表...")
        files = client.list_files()
        
        if files and 'data' in files:
            file_list = files['data'].get('list', [])
            print(f"✅ 找到 {len(file_list)} 个文件/文件夹")
            
            # 显示前3个文件
            for i, file_info in enumerate(file_list[:3]):
                name = file_info.get('file_name', '未知')
                size = file_info.get('size', 0)
                file_type = "文件夹" if file_info.get('file_type') == 0 else "文件"
                print(f"  {i+1}. {name} ({file_type}, {size} 字节)")
        
        # 获取存储信息
        print("\n💾 获取存储信息...")
        storage = client.get_storage_info()
        
        if storage and 'data' in storage:
            data = storage['data']
            total = data.get('total', 0)
            used = data.get('used', 0)
            
            print(f"✅ 总容量: {total / (1024**3):.2f} GB")
            print(f"✅ 已使用: {used / (1024**3):.2f} GB")
            print(f"✅ 剩余: {(total - used) / (1024**3):.2f} GB")
        
        # 获取分享列表
        print("\n🔗 获取分享列表...")
        shares = client.get_my_shares()
        
        if shares and 'data' in shares:
            share_list = shares['data'].get('list', [])
            print(f"✅ 找到 {len(share_list)} 个分享")
            
            for i, share_info in enumerate(share_list[:3]):
                title = share_info.get('title', '未命名')
                url = share_info.get('share_url', '')
                print(f"  {i+1}. {title} - {url}")
        
        print("\n🎉 API功能测试完成！")
        
    except Exception as e:
        print(f"❌ API测试失败: {e}")


def demo_fallback():
    """演示回退机制"""
    print("\n🔄 回退机制演示")
    print("=" * 50)
    
    print("📝 说明:")
    print("如果二维码登录失败（网络问题、页面变化等），")
    print("系统会自动回退到手动登录模式。")
    print()
    
    choice = input("是否演示回退机制？(y/n): ").lower().strip()
    
    if choice != 'y':
        print("⏭️ 跳过回退演示")
        return
    
    try:
        print("🚀 模拟二维码登录失败...")
        
        with QuarkClient(auto_login=False) as client:
            # 强制禁用二维码登录，触发回退
            cookies = client.login(force_relogin=True, use_qr=False)
            
            if cookies:
                print("✅ 回退到手动登录成功！")
                test_api(client)
            else:
                print("❌ 手动登录也失败了")
                
    except Exception as e:
        print(f"❌ 回退演示失败: {e}")


def main():
    """主函数"""
    print("🔲 夸克网盘二维码登录功能演示")
    print("=" * 60)
    
    print("📋 可用演示:")
    print("1. 二维码登录演示")
    print("2. 回退机制演示")
    print("3. 全部演示")
    
    choice = input("\n请选择演示类型 (1-3): ").strip()
    
    if choice == '1':
        demo_qr_login()
    elif choice == '2':
        demo_fallback()
    elif choice == '3':
        demo_qr_login()
        demo_fallback()
    else:
        print("❌ 无效选择")
        return
    
    print("\n🎉 演示完成！")
    print("\n📝 总结:")
    print("✅ 二维码登录提供了更便捷的认证方式")
    print("✅ 自动回退机制确保了系统的可靠性")
    print("✅ 无缝集成到现有API中，使用简单")


if __name__ == "__main__":
    main()
