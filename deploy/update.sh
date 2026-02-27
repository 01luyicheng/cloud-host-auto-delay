#!/bin/bash
#
# 文件用途: 更新程序脚本
# 创建日期: 2026-02-22
# 使用方法: sudo bash update.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/abeiyun"
SERVICE_NAME="abeiyun"

echo "========================================"
echo "云主机自动延期程序 - 更新脚本"
echo "========================================"

if [ "$EUID" -ne 0 ]; then
    echo "错误: 请使用root权限运行此脚本"
    exit 1
fi

echo "停止服务..."
systemctl stop $SERVICE_NAME || true

echo "备份配置文件..."
cp "$INSTALL_DIR/.env" /tmp/abeiyun.env.bak 2>/dev/null || true
cp "$INSTALL_DIR/config/accounts.json" /tmp/abeiyun_accounts.json.bak 2>/dev/null || true
cp "$INSTALL_DIR/data/account_state.json" /tmp/abeiyun_account_state.json.bak 2>/dev/null || true
cp "$INSTALL_DIR/data/delay_state.json" /tmp/abeiyun_delay_state.json.bak 2>/dev/null || true
cp "$INSTALL_DIR/data/email_rate.json" /tmp/abeiyun_email_rate.json.bak 2>/dev/null || true

echo "更新程序文件..."
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"

echo "恢复配置文件..."
cp /tmp/abeiyun.env.bak "$INSTALL_DIR/.env" 2>/dev/null || true
cp /tmp/abeiyun_accounts.json.bak "$INSTALL_DIR/config/accounts.json" 2>/dev/null || true
cp /tmp/abeiyun_account_state.json.bak "$INSTALL_DIR/data/account_state.json" 2>/dev/null || true
cp /tmp/abeiyun_delay_state.json.bak "$INSTALL_DIR/data/delay_state.json" 2>/dev/null || true
cp /tmp/abeiyun_email_rate.json.bak "$INSTALL_DIR/data/email_rate.json" 2>/dev/null || true

echo "更新依赖..."
cd "$INSTALL_DIR"
source venv/bin/activate
pip install --upgrade pip || { echo "警告: pip升级失败"; }
pip install -r requirements.txt || { echo "错误: 依赖安装失败"; exit 1; }
deactivate

echo "清理临时文件..."
rm -f /tmp/abeiyun*.bak

echo "重新加载systemd..."
systemctl daemon-reload

echo "启动服务..."
systemctl start $SERVICE_NAME

sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    echo "更新完成，服务运行正常"
else
    echo "错误: 服务启动失败"
    journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi
