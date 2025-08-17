#!/usr/bin/env python3
"""
QuarkPan 安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 读取requirements文件
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="quarkpan",
    version="1.0.0",
    description="夸克网盘 Python 客户端和命令行工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="QuarkPan Team",
    author_email="contact@quarkpan.dev",
    url="https://github.com/your-username/QuarkPan",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "quarkpan=quark_client.cli.main:app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
        "Topic :: System :: Archiving",
        "Topic :: Utilities",
    ],
    keywords="quark pan cloud storage cli api client",
    project_urls={
        "Bug Reports": "https://github.com/your-username/QuarkPan/issues",
        "Source": "https://github.com/your-username/QuarkPan",
        "Documentation": "https://github.com/your-username/QuarkPan/blob/main/docs/",
    },
)
