#!/bin/bash
#
# 修复部署脚本
#

set -e

echo "========================================"
echo "修复部署"
echo "========================================"
echo ""

cd /opt/abeiyun

# 1. 安装 python3-venv
echo "[1/5] 安装 python3-venv..."
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip

# 2. 删除旧的虚拟环境
echo ""
echo "[2/5] 清理旧环境..."
rm -rf venv

# 3. 创建虚拟环境
echo ""
echo "[3/5] 创建虚拟环境..."
python3 -m venv venv

# 4. 安装依赖
echo ""
echo "[4/5] 安装依赖..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# 5. 解压配置文件
echo ""
echo "[5/5] 解压配置文件..."
if [ -f /tmp/deploy-files.tar.gz ]; then
    tar -xzvf /tmp/deploy-files.tar.gz
    echo "配置文件已解压"
fi

# 6. 启动服务
echo ""
echo "启动服务..."
systemctl restart abeiyun
sleep 2

if systemctl is-active --quiet abeiyun; then
    echo ""
    echo "========================================"
    echo "修复成功!"
    echo "========================================"
    systemctl status abeiyun --no-pager
else
    echo ""
    echo "========================================"
    echo "启动失败!"
    echo "========================================"
    journalctl -u abeiyun -n 20 --no-pager
fi
