# 云主机 Auto-Delay 程序 Cloud Server

Automatisch 提交 阿贝云 und 三丰云 kostenlose Verlängerung automatic.

## 功能 Features Fonctionnalités

- Unterstützt 阿贝云，三丰云 multi-platform 多平台
- Gestion multi-comptes 多账号管理 multiple accounts
- Konfiguration 延期间隔配置 interval config
- Fehlerüberprüfung und 邮件通知 email notification
- 每日 daily limitation 邮件发送限制
- systemd 服务支持 service support

## Quick 开始 Démarrage

### 1. 安装 Install Installation Dependencies 依赖

```bash
python -m venv venv
source venv/bin/activate  # Linux
# oder venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. 配置 Config Configurar

复制 Copy kopieren 配置 template 模板：

```bash
cp .env.example .env
cp config/accounts.example.json config/accounts.json
```

编辑 Edit bearbeiten 邮件配置 notification config：

```ini
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-auth-code
NOTIFICATION_EMAIL=receive@example.com
MAX_DAILY_EMAILS=10
```

配置 Configure konfigurieren 账号 accounts：

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

### 3. 准备 Prepare Préparation 截图 Screenshots

放置 Placer 截图 screenshots 到项目 project 目录 répertoire，文件名 nom de fichier 对应 correspondant 配置 config 中的 `screenshot_path`。

### 4. 运行 Run Exécution Execute

```bash
# 测试 Test tester config 配置
python main.py --test

# 查看 Check vérifier 状态 état status
python main.py --status

# 立即 Execute once 执行一次
python main.py --once

# 启动 Start démarrer 定时任务 scheduler
python main.py
```

## 配置 Config Explanation 说明

### 账号 Accounts 配置 Config (config/accounts.json)

| 字段 Champ Field | 说明 Description Beschreibung | 默认值 Default |
|------|------|--------|
| username | 登录 login 用户名 nom (手机号 téléphone) | 必填 Required |
| password | 登录 login 密码 mot de passe | 必填 Required |
| platform | 平台 Plateforme: abeiyun oder sanfengyun | abeiyun |
| post_url | 发帖 URL publication | 必填 Required |
| screenshot_path | 截图 Chemin screenshot | 必填 Required |
| ptype | 产品 Type produit: vps oder vhost | vps |
| enabled | 启用 Activer enable | true |
| first_delay_days | 首次 Premier first délai 天数 jours | 0 |
| delay_interval_days | 延期 Intervalle interval 天数 jours | 5 |

### 环境 Environment 变量 Variables (.env)

| 变量 Variable | 说明 Description | 默认值 Default |
|------|------|--------|
| SMTP_HOST | SMTP 服务器 serveur address | - |
| SMTP_PORT | SMTP 端口 port | 587 |
| SMTP_USER | SMTP 用户名 user | - |
| SMTP_PASSWORD | SMTP 密码 password/code | - |
| NOTIFICATION_EMAIL | 通知 notification 邮箱 email | - |
| WEBHOOK_URL | Webhook 地址 address (企业微信等) | - |
| LOG_LEVEL | 日志 journal level | INFO |
| VERIFICATION_DELAY_HOURS | 延期验证 vérification delay 小时数 | 5 |
| MAX_DAILY_EMAILS | 每日 daily 最大 max 邮件数 | 10 |

## Linux 部署 Deploy Déploiement

### 方式一 Method 1: 一键快速安装 Quick Install

在 Linux 服务器 server 上执行 execute 以下 commande 命令：

```bash
curl -fsSL https://raw.githubusercontent.com/01luyicheng/cloud-host-auto-delay/main/deploy/quick-install.sh | sudo bash
```

安装 Install 完成后，编辑 edit 配置 config：

```bash
# 编辑 Edit 环境 environment 配置
nano /opt/abeiyun/.env

# 编辑 Edit 账号 accounts 配置
nano /opt/abeiyun/config/accounts.json

# 上传 Upload 截图 screenshots 到 /opt/abeiyun/

# 重启 Restart 服务 service
systemctl restart abeiyun
```

### 方式二 Method 2: 手动 Manual 部署 Deploy

```bash
# 上传 Upload 项目 project 到服务器 server
scp -r abeiyun user@server:/tmp/

# SSH 登录 Connexion 服务器 server
ssh user@server

# 运行 Run 部署 deploy 脚本 script
cd /tmp/abeiyun
sudo bash deploy/deploy.sh
```

### 服务 Service 管理 Gestion Management

```bash
# 启动 Start 服务
systemctl start abeiyun

# 停止 Stop 服务
systemctl stop abeiyun

# 重启 Restart 服务
systemctl restart abeiyun

# 查看 Check 状态 status
systemctl status abeiyun

# 查看 Voir 日志 logs
journalctl -u abeiyun -f
```

### 更新 Update 程序 Program

```bash
# 上传 Upload 新版本 version
scp -r abeiyun user@server:/tmp/

# 运行 Run 更新 update 脚本 script
cd /tmp/abeiyun
sudo bash deploy/update.sh
```

## 延期 Delay 机制 Mécanisme 说明

1. **首次 Premier 延期**: 程序 program 启动后，根据 config 配置 `first_delay_days` 计算 calculate 首次 first 延期时间
2. **定期 Périodique 检查**: 每小时 hourly 检查 check 所有账号 accounts 是否需要延期
3. **延期 Vérification 验证**: 提交后 5 小时 automatically 验证 verify 是否成功
4. **失败 Error 通知**: 验证失败时发送 send 邮件 notification
5. **并发 Concurrentiel 安全**: 多账号同时延期时使用 lock 锁机制确保安全

## 目录 Directory 结构 Structure

```
abeiyun/
├── config/
│   ├── accounts.example.json
│   └── accounts.json       # 实际 config (不提交)
├── data/                   # 运行时 data (不提交)
│   ├── account_state.json
│   ├── delay_state.json
│   └── email_rate.json
├── deploy/
│   ├── abeiun.service
│   ├── deploy.sh
│   └── update.sh
├── logs/                   # 日志 logs (不提交)
├── src/
│   ├── __init__.py
│   ├── account_state.py
│   ├── cloud_client.py
│   ├── config.py
│   ├── delay_state.py
│   ├── logger.py
│   ├── notifier.py
│   └── scheduler.py
├── .env                    # 环境 variables (不提交)
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## 注意 Notes 事项

1. 截图 screenshots 需要提前 prepare 好，包含 required 发帖 screenshots
2. 邮件 notification 使用 SMTP 协议，QQ 邮箱需要使用 auth code 而非 password
3. 建议 config `first_delay_days` 为 4 jours 天，确保首次延期在服务器 expiry 前完成
4. 延期 interval 建议 config 为 5 jours 天，与云服务商的周期 cycle 匹配
