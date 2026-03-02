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
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root权限运行此脚本"
        log_info "使用方法: curl -fsSL ... | sudo bash"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log_info "检测到操作系统: $NAME $VERSION_ID"
    elif [ -f /etc/redhat-release ]; then
        OS="rhel"
        log_info "检测到操作系统: RHEL/CentOS"
    elif [ -f /etc/debian_version ]; then
        OS="debian"
        log_info "检测到操作系统: Debian"
    else
        log_error "无法识别操作系统"
        exit 1
    fi
}

install_system_dependencies() {
    log_step "安装系统依赖..."
    
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y -qq python3 python3-venv python3-pip git curl
            ;;
        centos|rhel|fedora|rocky|almalinux)
            if command -v dnf &> /dev/null; then
                dnf install -y python3 python3-venv python3-pip git curl
            else
                yum install -y python3 python3-venv python3-pip git curl
            fi
            ;;
        alpine)
            apk add --no-cache python3 py3-virtualenv py3-pip git curl bash
            ;;
        *)
            log_warn "未知操作系统，尝试使用通用方法安装..."
            if command -v apt-get &> /dev/null; then
                apt-get update -qq
                apt-get install -y -qq python3 python3-venv python3-pip git curl
            elif command -v yum &> /dev/null; then
                yum install -y python3 python3-venv python3-pip git curl
            elif command -v apk &> /dev/null; then
                apk add --no-cache python3 py3-virtualenv py3-pip git curl bash
            else
                log_error "无法安装系统依赖，请手动安装 python3, python3-venv, python3-pip, git, curl"
                exit 1
            fi
            ;;
    esac
    
    log_info "系统依赖安装完成"
}

check_python() {
    log_step "检查Python环境..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "未找到Python"
        install_system_dependencies
        
        # 再次检查
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        else
            log_error "Python安装失败"
            exit 1
        fi
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
    
    # 检查Python版本是否>=3.8
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        log_error "Python版本过低，需要3.8或更高版本"
        exit 1
    fi
}

check_git() {
    log_step "检查Git..."
    
    if ! command -v git &> /dev/null; then
        log_warn "未找到Git，正在安装..."
        install_system_dependencies
    fi
    
    log_info "Git已安装"
}

download_project() {
    log_step "下载项目..."
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "目录已存在，正在更新..."
        cd "$INSTALL_DIR"
        
        # 备份现有配置
        if [ -f ".env" ]; then
            cp .env /tmp/abeiyun.env.backup
            log_info "已备份 .env 到 /tmp/abeiyun.env.backup"
        fi
        if [ -f "config/accounts.json" ]; then
            cp config/accounts.json /tmp/abeiyun.accounts.json.backup
            log_info "已备份 accounts.json 到 /tmp/abeiyun.accounts.json.backup"
        fi
        
        git pull --quiet
    else
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    log_info "项目下载完成"
}

setup_virtualenv() {
    log_step "设置Python虚拟环境..."
    
    # 检查并安装 python3-venv
    if ! $PYTHON_CMD -m venv --help &> /dev/null; then
        log_warn "python3-venv 未安装，正在安装..."
        install_system_dependencies
    fi
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        $PYTHON_CMD -m venv venv
    else
        log_info "虚拟环境已存在"
    fi
    
    log_info "激活虚拟环境并安装依赖..."
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip -q
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -q
    else
        log_error "未找到 requirements.txt"
        exit 1
    fi
    
    deactivate
    log_info "依赖安装完成"
}

setup_directories() {
    log_step "创建必要目录..."
    
    mkdir -p logs data config
    chmod 755 logs data
    
    log_info "目录创建完成"
}

setup_config() {
    log_step "配置检查..."
    
    # 恢复备份的配置
    if [ -f "/tmp/abeiyun.env.backup" ]; then
        cp /tmp/abeiyun.env.backup .env
        log_info "已恢复 .env 配置"
    elif [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "已创建 .env 文件，请编辑配置后重启服务"
            log_info "编辑命令: nano $INSTALL_DIR/.env"
        fi
    fi
    
    if [ -f "/tmp/abeiyun.accounts.json.backup" ]; then
        cp /tmp/abeiyun.accounts.json.backup config/accounts.json
        log_info "已恢复 accounts.json 配置"
    elif [ ! -f "config/accounts.json" ]; then
        if [ -f "config/accounts.example.json" ]; then
            cp config/accounts.example.json config/accounts.json
            log_warn "已创建 config/accounts.json，请编辑配置后重启服务"
            log_info "编辑命令: nano $INSTALL_DIR/config/accounts.json"
        fi
    fi
}

install_service() {
    log_step "安装系统服务..."
    
    # 创建systemd服务文件
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Cloud Host Auto Delay Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PYTHONUNBUFFERED=1"
Environment="LANG=en_US.UTF-8"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/service.log
StandardError=append:$INSTALL_DIR/logs/service.log

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    log_info "服务安装完成"
}

start_service() {
    log_step "启动服务..."
    
    systemctl start $SERVICE_NAME
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "服务启动成功!"
    else
        log_error "服务启动失败"
        log_info "查看日志: journalctl -u $SERVICE_NAME -n 20 --no-pager"
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
    
    # 检查是否需要配置
    if [ -f ".env" ]; then
        if grep -q "your-email@qq.com" .env 2>/dev/null || grep -q "your-password" .env 2>/dev/null; then
            log_warn "请编辑 .env 文件配置真实信息"
            echo "  编辑命令: nano $INSTALL_DIR/.env"
        fi
    fi
    
    if [ -f "config/accounts.json" ]; then
        if grep -q "手机号" config/accounts.json 2>/dev/null; then
            log_warn "请编辑 accounts.json 配置真实账号"
            echo "  编辑命令: nano $INSTALL_DIR/config/accounts.json"
        fi
    fi
    
    echo ""
}

main() {
    echo "========================================"
    echo "云主机自动延期程序 - 快速安装"
    echo "========================================"
    echo ""
    
    check_root
    detect_os
    check_python
    check_git
    download_project
    setup_virtualenv
    setup_directories
    setup_config
    install_service
    start_service
    show_info
}

main "$@"
