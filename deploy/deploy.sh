#!/bin/bash
#
# 文件用途: Linux部署脚本
# 创建日期: 2026-02-22
# 使用方法: sudo bash deploy.sh
#
# 实现说明:
# 1. 检查运行环境
# 2. 安装Python依赖
# 3. 配置systemd服务
# 4. 启动服务
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/abeiyun"
SERVICE_NAME="abeiyun"

echo "========================================"
echo "云主机自动延期程序 - Linux部署脚本"
echo "========================================"
echo ""

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "错误: 请使用root权限运行此脚本"
        echo "使用方法: sudo bash $0"
        exit 1
    fi
}

check_python() {
    echo "检查Python环境..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -p python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "错误: 未找到Python，请先安装Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    echo "Python版本: $PYTHON_VERSION"
    
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        echo "错误: Python版本过低，需要3.8或更高版本"
        exit 1
    fi
}

install_dependencies() {
    echo ""
    echo "安装依赖..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -d "venv" ]; then
        echo "创建虚拟环境..."
        if ! $PYTHON_CMD -m venv venv; then
            echo "错误: 虚拟环境创建失败"
            exit 1
        fi
    fi
    
    echo "激活虚拟环境并安装依赖..."
    source venv/bin/activate
    pip install --upgrade pip || { echo "错误: pip升级失败"; exit 1; }
    pip install -r requirements.txt || { echo "错误: 依赖安装失败"; exit 1; }
    deactivate
    
    echo "依赖安装完成"
}

setup_config() {
    echo ""
    echo "检查配置文件..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            echo "请先配置 .env 文件"
            echo "可以复制 .env.example 为 .env 并填写真实配置"
            cp .env.example .env
            echo "已创建 .env 文件，请编辑后重新运行部署"
            exit 1
        else
            echo "错误: 未找到 .env.example 文件"
            exit 1
        fi
    fi
    
    if [ ! -f "config/accounts.json" ]; then
        if [ -f "config/accounts.example.json" ]; then
            echo "请先配置 config/accounts.json 文件"
            echo "可以复制 config/accounts.example.json 为 config/accounts.json 并填写真实配置"
            cp config/accounts.example.json config/accounts.json
            echo "已创建 config/accounts.json 文件，请编辑后重新运行部署"
            exit 1
        else
            echo "错误: 未找到 config/accounts.example.json 文件"
            exit 1
        fi
    fi
    
    echo "配置文件检查通过"
}

install_service() {
    echo ""
    echo "安装systemd服务..."
    
    mkdir -p "$INSTALL_DIR"
    
    cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
    
    cp "$SCRIPT_DIR/abeiyun.service" /etc/systemd/system/
    
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/data"
    
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    echo "服务安装完成"
}

start_service() {
    echo ""
    echo "启动服务..."
    
    systemctl start $SERVICE_NAME
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "服务启动成功"
        systemctl status $SERVICE_NAME --no-pager
    else
        echo "错误: 服务启动失败"
        journalctl -u $SERVICE_NAME -n 20 --no-pager
        exit 1
    fi
}

show_info() {
    echo ""
    echo "========================================"
    echo "部署完成!"
    echo "========================================"
    echo ""
    echo "服务管理命令:"
    echo "  启动服务:   systemctl start $SERVICE_NAME"
    echo "  停止服务:   systemctl stop $SERVICE_NAME"
    echo "  重启服务:   systemctl restart $SERVICE_NAME"
    echo "  查看状态:   systemctl status $SERVICE_NAME"
    echo "  查看日志:   journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "文件位置:"
    echo "  程序目录:   $INSTALL_DIR"
    echo "  配置文件:   $INSTALL_DIR/.env"
    echo "  账号配置:   $INSTALL_DIR/config/accounts.json"
    echo "  日志目录:   $INSTALL_DIR/logs"
    echo ""
}

main() {
    check_root
    check_python
    install_dependencies
    setup_config
    install_service
    start_service
    show_info
}

main "$@"
