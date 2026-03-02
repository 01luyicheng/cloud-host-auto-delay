#!/bin/bash
#
# 快速安装脚本 - 一键部署云主机自动延期程序
# 使用方法: curl -fsSL https://raw.githubusercontent.com/01luyicheng/cloud-host-auto-delay/main/deploy/quick-install.sh | sudo bash
#

set -e

REPO_URL="https://github.com/01luyicheng/cloud-host-auto-delay.git"
INSTALL_DIR="/opt/abeiyun"
SERVICE_NAME="abeiyun"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root权限运行此脚本"
        log_info "使用方法: curl -fsSL ... | sudo bash"
        exit 1
    fi
}

check_system() {
    log_info "检查系统环境..."
    
    # 检查操作系统
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        log_info "操作系统: $OS"
    else
        log_warn "无法识别操作系统"
    fi
    
    # 检查Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "未找到Python，正在尝试安装..."
        install_python
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_warn "未找到Git，正在安装..."
        install_git
    fi
}

install_python() {
    log_info "安装Python..."
    if [ -f /etc/debian_version ]; then
        apt-get update -qq
        apt-get install -y -qq python3 python3-venv python3-pip
        PYTHON_CMD="python3"
    elif [ -f /etc/redhat-release ]; then
        yum install -y python3 python3-venv python3-pip
        PYTHON_CMD="python3"
    else
        log_error "不支持的操作系统，请手动安装Python 3.8+"
        exit 1
    fi
}

install_git() {
    if [ -f /etc/debian_version ]; then
        apt-get update -qq
        apt-get install -y -qq git
    elif [ -f /etc/redhat-release ]; then
        yum install -y git
    fi
}

download_project() {
    log_info "下载项目..."
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "目录已存在，正在更新..."
        cd "$INSTALL_DIR"
        git pull --quiet
    else
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    log_info "项目下载完成"
}

install_dependencies() {
    log_info "安装依赖..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
    fi
    
    # 使用国内镜像加速
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    deactivate
    
    log_info "依赖安装完成"
}

setup_config() {
    log_info "配置检查..."
    
    # 创建必要目录
    mkdir -p logs data config
    
    # 检查配置文件
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "已创建 .env 文件，请编辑配置后重启服务"
        fi
    fi
    
    if [ ! -f "config/accounts.json" ]; then
        if [ -f "config/accounts.example.json" ]; then
            cp config/accounts.example.json config/accounts.json
            log_warn "已创建 config/accounts.json，请编辑配置后重启服务"
        fi
    fi
}

install_service() {
    log_info "安装系统服务..."
    
    # 创建systemd服务文件
    cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=Cloud Host Auto Delay Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/abeiyun
Environment="PYTHONUNBUFFERED=1"
Environment="LANG=en_US.UTF-8"
ExecStart=/opt/abeiyun/venv/bin/python /opt/abeiyun/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/abeiyun/logs/service.log
StandardError=append:/opt/abeiyun/logs/service.log

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    log_info "服务安装完成"
}

start_service() {
    log_info "启动服务..."
    
    systemctl start $SERVICE_NAME
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "服务启动成功!"
    else
        log_error "服务启动失败，查看日志:"
        journalctl -u $SERVICE_NAME -n 10 --no-pager
        exit 1
    fi
}

show_info() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}部署完成!${NC}"
    echo "========================================"
    echo ""
    echo "服务管理命令:"
    echo "  启动:   systemctl start $SERVICE_NAME"
    echo "  停止:   systemctl stop $SERVICE_NAME"
    echo "  重启:   systemctl restart $SERVICE_NAME"
    echo "  状态:   systemctl status $SERVICE_NAME"
    echo "  日志:   journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "文件位置:"
    echo "  程序目录: $INSTALL_DIR"
    echo "  配置文件: $INSTALL_DIR/.env"
    echo "  账号配置: $INSTALL_DIR/config/accounts.json"
    echo "  日志目录: $INSTALL_DIR/logs"
    echo ""
    echo "下一步:"
    echo "  1. 编辑配置文件: nano $INSTALL_DIR/.env"
    echo "  2. 编辑账号配置: nano $INSTALL_DIR/config/accounts.json"
    echo "  3. 重启服务: systemctl restart $SERVICE_NAME"
    echo ""
}

main() {
    echo "========================================"
    echo "云主机自动延期程序 - 快速安装"
    echo "========================================"
    echo ""
    
    check_root
    check_system
    download_project
    install_dependencies
    setup_config
    install_service
    start_service
    show_info
}

main "$@"
