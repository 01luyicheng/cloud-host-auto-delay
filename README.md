# 云主机免费服务器自动延期程序

自动提交阿贝云和三丰云免费服务器延期申请。

## 功能特性

- 支持阿贝云、三丰云多平台
- 支持多账号管理
- 账号级别的延期间隔配置
- 延期失败自动验证和邮件通知
- 每日邮件发送限制
- systemd服务支持

## 快速开始

### 1. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Linux
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. 配置

复制配置文件模板：

```bash
cp .env.example .env
cp config/accounts.example.json config/accounts.json
```

编辑 `.env` 配置邮件通知（可选）：

```ini
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-auth-code
NOTIFICATION_EMAIL=receive@example.com
MAX_DAILY_EMAILS=10
```

编辑 `config/accounts.json` 配置账号：

```json
{
  "global": {
    "first_delay_days": 4,
    "delay_interval_days": 5
  },
  "accounts": [
    {
      "username": "手机号",
      "password": "密码",
      "platform": "abeiyun",
      "post_url": "https://blog.csdn.net/xxx/article/details/xxx",
      "screenshot_path": "./abeiyun_screenshot.jpg",
      "enabled": true,
      "first_delay_days": 4,
      "delay_interval_days": 5
    }
  ]
}
```

### 3. 准备截图

将延期申请所需的截图放到项目目录下，文件名与配置中的 `screenshot_path` 对应。

### 4. 运行

```bash
# 测试配置
python main.py --test

# 查看状态
python main.py --status

# 立即执行一次
python main.py --once

# 启动定时任务
python main.py
```

## 配置说明

### 账号配置 (config/accounts.json)

| 字段 | 说明 | 默认值 |
|------|------|--------|
| username | 登录用户名（手机号） | 必填 |
| password | 登录密码 | 必填 |
| platform | 平台：abeiyun 或 sanfengyun | abeiyun |
| post_url | 发帖地址 | 必填 |
| screenshot_path | 截图路径 | 必填 |
| ptype | 产品类型：vps 或 vhost | vps |
| enabled | 是否启用 | true |
| first_delay_days | 首次延期天数（从现在开始） | 0 |
| delay_interval_days | 延期间隔天数 | 5 |

### 环境变量 (.env)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SMTP_HOST | SMTP服务器地址 | - |
| SMTP_PORT | SMTP端口 | 587 |
| SMTP_USER | SMTP用户名 | - |
| SMTP_PASSWORD | SMTP密码/授权码 | - |
| NOTIFICATION_EMAIL | 接收通知的邮箱 | - |
| WEBHOOK_URL | Webhook地址（企业微信等） | - |
| LOG_LEVEL | 日志级别 | INFO |
| VERIFICATION_DELAY_HOURS | 延期验证延迟小时数 | 5 |
| MAX_DAILY_EMAILS | 每日最大邮件数 | 10 |

## Linux部署

### 方式一：一键快速安装（推荐）

在Linux服务器上直接执行以下命令：

```bash
curl -fsSL https://raw.githubusercontent.com/01luyicheng/cloud-host-auto-delay/main/deploy/quick-install.sh | sudo bash
```

安装完成后，编辑配置文件：

```bash
# 编辑环境配置
nano /opt/abeiyun/.env

# 编辑账号配置
nano /opt/abeiyun/config/accounts.json

# 上传截图文件到 /opt/abeiyun/

# 重启服务
systemctl restart abeiyun
```

### 方式二：手动部署

```bash
# 上传项目到服务器
scp -r abeiyun user@server:/tmp/

# SSH登录服务器
ssh user@server

# 运行部署脚本
cd /tmp/abeiyun
sudo bash deploy/deploy.sh
```

### 服务管理

```bash
# 启动服务
systemctl start abeiyun

# 停止服务
systemctl stop abeiyun

# 重启服务
systemctl restart abeiyun

# 查看状态
systemctl status abeiyun

# 查看日志
journalctl -u abeiyun -f
```

### 更新程序

```bash
# 上传新版本
scp -r abeiyun user@server:/tmp/

# 运行更新脚本
cd /tmp/abeiyun
sudo bash deploy/update.sh
```

## 延期机制说明

1. **首次延期**: 程序启动后，根据 `first_delay_days` 配置计算首次延期时间
2. **定期检查**: 每小时检查一次所有账号是否需要延期
3. **延期验证**: 延期提交后5小时自动验证是否成功
4. **失败通知**: 验证失败时发送邮件通知
5. **并发安全**: 多账号同时延期时使用锁机制确保安全

## 目录结构

```
abeiyun/
├── config/
│   ├── accounts.example.json
│   └── accounts.json       # 实际配置（不提交）
├── data/                   # 运行时数据（不提交）
│   ├── account_state.json
│   ├── delay_state.json
│   └── email_rate.json
├── deploy/
│   ├── abeiun.service
│   ├── deploy.sh
│   └── update.sh
├── logs/                   # 日志文件（不提交）
├── src/
│   ├── __init__.py
│   ├── account_state.py
│   ├── cloud_client.py
│   ├── config.py
│   ├── delay_state.py
│   ├── logger.py
│   ├── notifier.py
│   └── scheduler.py
├── .env                    # 环境变量（不提交）
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## 注意事项

1. 截图文件需要提前准备好，包含延期申请所需的发帖截图
2. 邮件通知使用SMTP协议，QQ邮箱需要使用授权码而非密码
3. 建议设置 `first_delay_days` 为4天，确保首次延期在服务器到期前完成
4. 延期间隔建议设置为5天，与云服务商的延期周期匹配
