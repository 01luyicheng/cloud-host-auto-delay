#!/bin/bash
#
# 服务器部署脚本 - 在目标服务器上执行
#

set -e

echo "========================================"
echo "云主机自动延期程序 - 服务器部署"
echo "========================================"
echo ""

# 1. 安装程序
echo "[1/4] 安装程序..."
cd /tmp
curl -fsSL https://raw.githubusercontent.com/01luyicheng/cloud-host-auto-delay/main/deploy/quick-install.sh -o quick-install.sh
bash quick-install.sh

# 2. 解压配置文件
echo ""
echo "[2/4] 解压配置文件..."
cd /opt/abeiyun
if [ -f /tmp/deploy-files.tar.gz ]; then
    tar -xzvf /tmp/deploy-files.tar.gz
    echo "配置文件已解压"
else
    echo "警告: 未找到 deploy-files.tar.gz，请手动上传配置文件"
fi

# 3. 设置权限
echo ""
echo "[3/4] 设置权限..."
mkdir -p logs data
chmod 755 logs data

# 4. 启动服务
echo ""
echo "[4/4] 启动服务..."
systemctl restart abeiyun
sleep 2

if systemctl is-active --quiet abeiyun; then
    echo ""
    echo "========================================"
    echo "部署成功!"
    echo "========================================"
    echo ""
    echo "服务状态:"
    systemctl status abeiyun --no-pager
    echo ""
    echo "查看日志: journalctl -u abeiyun -f"
    echo ""
else
    echo ""
    echo "========================================"
    echo "部署失败!"
    echo "========================================"
    echo ""
    echo "查看错误日志:"
    journalctl -u abeiyun -n 20 --no-pager
    exit 1
fi
