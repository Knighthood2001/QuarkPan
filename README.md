# QuarkPan - 夸克网盘 Python 客户端

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-brightgreen.svg)]()

一个功能完整、高性能的夸克网盘 Python API 客户端，支持文件管理、分享转存等核心功能。

## ✨ 特性

### 🗂️ 文件管理
- **文件浏览**: 获取文件列表，支持分页和排序
- **文件操作**: 创建、删除、移动、重命名文件和文件夹
- **文件搜索**: 支持关键词搜索和高级筛选
- **下载支持**: 获取直接下载链接

### 🔄 分享转存
- **智能解析**: 自动识别分享链接格式和提取码
- **批量转存**: 支持多个分享链接批量处理
- **自定义过滤**: 按文件类型、大小等条件筛选转存
- **分享管理**: 创建、查看、删除分享链接

### 🚀 技术优势
- **高性能**: 直接 API 调用，比浏览器自动化快 10-100 倍
- **低资源**: 无需浏览器内核，内存占用小
- **易扩展**: 模块化设计，支持自定义扩展
- **类型安全**: 完整的类型注解和异常处理

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/QuarkPan.git
cd QuarkPan

# 安装依赖
pip install -r requirements.txt

# 安装浏览器（用于自动登录）
playwright install firefox
```

### 基础使用

```python
from quark_client import QuarkClient

# 创建客户端（首次使用会自动打开浏览器登录）
with QuarkClient() as client:
    # 获取文件列表
    files = client.list_files()
    print(f"找到 {len(files['data']['list'])} 个文件")
    
    # 搜索文件
    results = client.search_files("关键词")
    
    # 转存分享链接
    result = client.save_shared_files(
        "https://pan.quark.cn/s/abc123 密码: 1234"
    )
    
    # 批量转存
    results = client.batch_save_shares([
        "https://pan.quark.cn/s/link1",
        "https://pan.quark.cn/s/link2 密码: abcd"
    ])
```

## 📚 API 文档

### 认证管理

```python
from quark_client import QuarkAuth

# 二维码登录（推荐）
auth = QuarkAuth()
cookies = auth.login(use_qr=True)  # 自动提取二维码，扫码登录

# 手动登录（回退方案）
cookies = auth.login(use_qr=False)  # 打开浏览器手动登录

# 检查登录状态
if auth.is_logged_in():
    print("已登录")

# 登出
auth.logout()
```

### 文件管理

```python
# 获取文件列表
files = client.list_files(
    folder_id="0",      # 文件夹ID，"0"为根目录
    page=1,             # 页码
    size=50,            # 每页数量
    sort_field="file_name",  # 排序字段
    sort_order="asc"    # 排序方向
)

# 创建文件夹
result = client.create_folder("新文件夹", parent_id="0")

# 删除文件
result = client.delete_files(["file_id_1", "file_id_2"])

# 移动文件
result = client.move_files(["file_id"], "target_folder_id")

# 重命名文件
result = client.rename_file("file_id", "新名称")

# 搜索文件
results = client.search_files("关键词", folder_id="0")

# 获取下载链接
download_url = client.get_download_url("file_id")
```

### 分享管理

```python
# 创建分享
share = client.create_share(
    file_ids=["file_id_1", "file_id_2"],
    expire_days=7,      # 过期天数，0为永久
    password="1234",    # 提取码，None为无密码
    download_limit=0    # 下载次数限制，0为无限制
)

# 解析分享链接
share_id, password = client.parse_share_url(
    "https://pan.quark.cn/s/abc123 密码: 1234"
)

# 转存分享文件
result = client.save_shared_files(
    share_url="https://pan.quark.cn/s/abc123",
    target_folder_id="0",
    target_folder_name="转存文件夹"  # 可选
)

# 批量转存（带过滤器）
def video_filter(file_info):
    """只转存视频文件"""
    name = file_info.get('file_name', '').lower()
    return name.endswith(('.mp4', '.avi', '.mkv'))

results = client.batch_save_shares(
    share_urls=["链接1", "链接2"],
    target_folder_id="0",
    create_subfolder=True  # 为每个分享创建子文件夹
)

# 获取我的分享
shares = client.get_my_shares(page=1, size=20)
```

## 🏗️ 项目结构

```
QuarkPan/
├── quark_client/           # 主要代码
│   ├── __init__.py        # 包入口
│   ├── client.py          # 主客户端类
│   ├── config.py          # 配置管理
│   ├── exceptions.py      # 异常定义
│   ├── auth/              # 认证模块
│   │   ├── __init__.py
│   │   └── login.py       # 登录实现
│   ├── core/              # 核心API客户端
│   │   ├── __init__.py
│   │   └── api_client.py  # HTTP客户端
│   └── services/          # 业务服务
│       ├── __init__.py
│       ├── file_service.py    # 文件管理
│       └── share_service.py   # 分享管理
├── examples/              # 使用示例
│   ├── basic_usage.py     # 基础使用
│   └── share_save_demo.py # 分享转存演示
├── docs/                  # 文档
│   └── api_analysis.md    # API分析文档
├── tests/                 # 测试脚本
├── requirements.txt       # 依赖列表
└── README.md             # 项目说明
```

## 🧪 测试

```bash
# 基础功能测试
python test_basic.py

# 登录功能测试
python test_login.py

# API功能测试
python test_api.py

# 运行示例
python examples/basic_usage.py
python examples/share_save_demo.py
```

## 📋 依赖

- **Python**: 3.8+
- **httpx**: HTTP客户端
- **playwright**: 浏览器自动化（用于登录）
- **typer**: 命令行界面
- **rich**: 美观的终端输出
- **pydantic**: 数据验证

## ⚠️ 注意事项

1. **首次使用**: 需要在浏览器中手动完成登录
2. **Cookie管理**: 登录信息会自动保存到 `config/cookies.json`
3. **安全性**: 请妥善保管配置目录，避免泄露登录信息
4. **使用限制**: 请遵守夸克网盘的使用条款，合理使用API
5. **法律责任**: 仅用于个人学习和合法用途

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

感谢以下项目提供的参考和灵感：
- [quark-auto-save](https://github.com/Cp0204/quark-auto-save) - 自动转存和媒体库整合
- [QuarkPanTool](https://github.com/ihmily/QuarkPanTool) - 批量操作工具

## 📞 支持

如果遇到问题，请：
1. 查看 [文档](docs/)
2. 搜索已有的 [Issues](https://github.com/your-username/QuarkPan/issues)
3. 提交新的 Issue 并附上详细信息
