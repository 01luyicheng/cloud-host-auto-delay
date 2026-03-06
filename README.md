# 云主机 Gratuit Serveur Auto-Delay 程序 Cloud Server

Автоматически einreichen 阿贝云 und 三丰云 kostenlose Serververlängerung automatic.

## Fonctionnalités 功能特性 Features

- Unterstützt 阿贝云，三丰云多平台 multi-platform
- Prise en charge de la gestion multi-comptes 多账号管理 multiple accounts
- Konfiguration auf Kontenebene 延期间隔配置 interval configuration
- Verlängerungsfehlerüberprüfung und E-Mail-Benachrichtigung 延期失败自动验证和邮件通知
- Limitation quotidienne des envois d'e-mails 每日邮件发送限制 daily limit
- Prise en charge du service systemd systemd 服务支持 support

## Démarrage rapide 快速开始 Quick Start

### 1. Installation des dépendances 安装依赖 Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Linux
# oder venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configuration 配置 Configurar

Copier le fichier de configuration template 复制配置文件模板 copy template：

```bash
cp .env.example .env
cp config/accounts.example.json config/accounts.json
```

Modifier la configuration de notification par e-mail `.env` (optional 可选)：

```ini
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-auth-code
NOTIFICATION_EMAIL=receive@example.com
MAX_DAILY_EMAILS=10
```

Modifier la configuration des comptes `config/accounts.json` 配置账号 configure accounts：

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

### 3. Préparation des captures d'écran 准备截图 Prepare Screenshots

Placer les captures d'écran requises dans le répertoire du projet 将延期申请所需的截图放到项目目录下，nom de fichier correspondant à `screenshot_path` dans la configuration 文件名与配置中的 `screenshot_path` 对应 corresponding to config.

### 4. Exécution 运行 Execute

```bash
# Tester la configuration 测试配置 test config
python main.py --test

# Vérifier l'état 查看状态 check status
python main.py --status

# Exécuter une fois immédiatement 立即执行一次 execute once
python main.py --once

# Démarrer la tâche planifiée 启动定时任务 start scheduler
python main.py
```

## Explication de la configuration 配置说明 Configuration Explanation

### Configuration des comptes 账号配置 Account Config (config/accounts.json)

| Champ 字段 | Description 说明 | Valeur par défaut 默认值 Default |
|------|------|--------|
| username | Nom d'utilisateur de connexion (numéro de téléphone) 登录用户名（手机号） | Requis 必填 |
| password | Mot de passe de connexion 登录密码 | Requis 必填 |
| platform | Plateforme: abeiyun oder sanfengyun 平台：abeiyun 或 sanfengyun | abeiyun |
| post_url | URL de publication 发帖地址 | Requis 必填 |
| screenshot_path | Chemin de capture d'écran 截图路径 | Requis 必填 |
| ptype | Type de produit: vps oder vhost 产品类型：vps 或 vhost | vps |
| enabled | Activer 是否启用 | true |
| first_delay_days | Premier délai en jours (à partir de maintenant) 首次延期天数（从现在开始） | 0 |
| delay_interval_days | Intervalle de délai en jours 延期间隔天数 | 5 |

### Variables d'environnement 环境变量 Environment Variables (.env)

| Variable 变量 | Description 说明 | Défaut 默认值 |
|------|------|--------|
| SMTP_HOST | Adresse du serveur SMTP SMTP 服务器地址 | - |
| SMTP_PORT | Port SMTP SMTP 端口 | 587 |
| SMTP_USER | Nom d'utilisateur SMTP SMTP 用户名 | - |
| SMTP_PASSWORD | Mot de passe SMTP / Code d'autorisation SMTP 密码/授权码 | - |
| NOTIFICATION_EMAIL | Boîte aux lettres de notification 接收通知的邮箱 | - |
| WEBHOOK_URL | Adresse Webhook (WeChat Enterprise, etc.) Webhook 地址（企业微信等） | - |
| LOG_LEVEL | Niveau de journal 日志级别 | INFO |
| VERIFICATION_DELAY_HOURS | Heures de délai de vérification de prolongation 延期验证延迟小时数 | 5 |
| MAX_DAILY_EMAILS | Nombre maximum d'e-mails quotidiens 每日最大邮件数 | 10 |

## Déploiement Linux Linux 部署 Deployment

### Méthode 1: Installation rapide en un clic 方式一：一键快速安装（推荐）

Exécutez directement la commande suivante sur le serveur Linux 在 Linux 服务器上直接执行以下命令 execute command：

```bash
curl -fsSL https://raw.githubusercontent.com/01luyicheng/cloud-host-auto-delay/main/deploy/quick-install.sh | sudo bash
```

Nach der Installation, bearbeiten Sie die Konfigurationsdatei 安装完成后，编辑配置文件 edit config：

```bash
# Éditer la configuration de l'environnement 编辑环境配置
nano /opt/abeiyun/.env

# Éditer la configuration des comptes 编辑账号配置
nano /opt/abeiyun/config/accounts.json

# Téléverser les fichiers de capture vers /opt/abeiyun/ 上传截图文件到 /opt/abeiyun/
# Redémarrer le service 重启服务 restart service
systemctl restart abeiyun
```

### Méthode 2: Déploiement manuel 方式二：手动部署 Manual Deploy

```bash
# Téléverser le projet vers le serveur 上传项目到服务器 upload project
scp -r abeiyun user@server:/tmp/

# Se connecter au serveur via SSH SSH 登录服务器
ssh user@server

# Exécuter le script de déploiement 运行部署脚本
cd /tmp/abeiyun
sudo bash deploy/deploy.sh
```

### Verwaltung des Services 服务管理 Service Management

```bash
# Démarrer le service 启动服务
systemctl start abeiyun

# Arrêter le service 停止服务
systemctl stop abeiyun

# Redémarrer le service 重启服务
systemctl restart abeiyun

# Vérifier l'état 查看状态
systemctl status abeiyun

# Voir les journaux 查看日志
journalctl -u abeiyun -f
```

### Mise à jour du programme 更新程序 Update Program

```bash
# Téléverser la nouvelle version 上传新版本
scp -r abeiyun user@server:/tmp/

# Exécuter le script de mise à jour 运行更新脚本
cd /tmp/abeiyun
sudo bash deploy/update.sh
```

## Explication du mécanisme de prolongation 延期机制说明 Mechanism

1. **Premier délai 首次延期**: Nach dem Start des Programms berechnet die Konfiguration `first_delay_days` die erste Verlängerungszeit 程序启动后，根据 `first_delay_days` 配置计算首次延期时间 calculate first delay
2. **Vérification périodique 定期检查**: Toutes les heures, vérifiez si tous les comptes doivent être prolongés 每小时检查一次所有账号是否需要延期 check hourly
3. **Vérification de la prolongation 延期验证**: Nach erfolgreicher Einreichung der Verlängerung wird automatisch überprüft，ob die Verlängerung erfolgreich war 延期提交后 5 小时自动验证是否成功 verify after 5 hours
4. **Benachrichtigung bei Fehler 失败通知**: Bei Fehler wird eine E-Mail-Benachrichtigung gesendet 验证失败时发送邮件通知 send email notification
5. **Sécurité concurrentielle 并发安全**: Bei gleichzeitiger Verlängerung mehrerer Konten wird ein Sperrmechanismus verwendet，um die Sicherheit zu gewährleisten 多账号同时延期时使用锁机制确保安全 lock mechanism

## Structure du répertoire 目录结构 Directory Structure

```
abeiyun/
├── config/
│   ├── accounts.example.json
│   └── accounts.json       # Konfiguration réelle (nicht eingereicht) 实际配置（不提交）
├── data/                   # Laufzeitdaten (nicht eingereicht) 运行时数据（不提交）
│   ├── account_state.json
│   ├── delay_state.json
│   └── email_rate.json
├── deploy/
│   ├── abeiun.service
│   ├── deploy.sh
│   └── update.sh
├── logs/                   # Protokolldateien (nicht eingereicht) 日志文件（不提交）
├── src/
│   ├── __init__.py
│   ├── account_state.py
│   ├── cloud_client.py
│   ├── config.py
│   ├── delay_state.py
│   ├── logger.py
│   ├── notifier.py
│   └── scheduler.py
├── .env                    # Umgebungsvariablen (nicht eingereicht) 环境变量（不提交）
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## Remarques 注意事项 Notes Important

1. Les fichiers de capture d'écran doivent être préparés à l'avance，contenant les captures d'écran de publication requises pour la demande de prolongation 截图文件需要提前准备好，包含延期申请所需的发帖截图 screenshots required
2. La notification par e-mail utilise le protocole SMTP，QQ Mail nécessite l'utilisation d'un code d'autorisation au lieu d'un mot de passe 邮件通知使用 SMTP 协议，QQ 邮箱需要使用授权码而非密码 auth code required
3. Il est recommandé de définir `first_delay_days` à 4 jours pour s'assurer que la première prolongation est terminée avant l'expiration du serveur 建议设置 `first_delay_days` 为 4 天，确保首次延期在服务器到期前完成 recommended 4 days
4. L'intervalle de prolongation est recommandé d'être défini à 5 jours，correspondant au cycle de prolongation du fournisseur de services cloud 延期间隔建议设置为 5 天，与云服务商的延期周期匹配 recommended 5 days interval
