"""
通知模块

文件用途: 发送延期任务执行结果的通知
创建日期: 2026-02-18
更新日期: 2026-02-22
输入: 通知内容、配置信息
输出: 发送结果
依赖: 无（可选依赖smtplib用于邮件通知）

实现说明:
1. 支持邮件通知（SMTP）
2. 支持Webhook通知（HTTP POST）
3. 支持多种通知渠道同时使用
4. 失败时记录日志但不影响主流程
5. 支持验证失败通知（延期未生效时提醒用户手动处理）
6. 支持每日邮件发送数量限制
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pathlib import Path
from threading import Lock

from src.logger import logger


class EmailRateLimiter:
    """
    邮件发送频率限制器
    
    实现说明:
    1. 记录每日发送数量
    2. 状态持久化到JSON文件
    3. 线程安全
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._state_lock = Lock()
        
        self.project_root = Path(__file__).parent.parent
        self.state_file = self.project_root / 'data' / 'email_rate.json'
        self.state_file.parent.mkdir(exist_ok=True)
        
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        with self._state_lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        self._state: Dict[str, Any] = json.load(f)
                except Exception as e:
                    logger.error(f'加载邮件频率状态失败: {e}')
                    self._state = {}
            else:
                self._state = {}
    
    def _save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f'保存邮件频率状态失败: {e}')
    
    def _get_today_key(self) -> str:
        """获取今日日期键"""
        return date.today().isoformat()
    
    def can_send(self, max_daily: int) -> bool:
        """
        检查是否可以发送邮件
        
        Args:
            max_daily: 每日最大发送数量
            
        Returns:
            是否可以发送
        """
        if max_daily <= 0:
            return True
        
        with self._state_lock:
            today_key = self._get_today_key()
            today_count = self._state.get(today_key, 0)
            return today_count < max_daily
    
    def record_send(self):
        """记录一次发送"""
        with self._state_lock:
            today_key = self._get_today_key()
            self._state[today_key] = self._state.get(today_key, 0) + 1
            self._save_state()
    
    def get_today_count(self) -> int:
        """获取今日已发送数量"""
        with self._state_lock:
            today_key = self._get_today_key()
            return self._state.get(today_key, 0)
    
    def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        from datetime import timedelta
        
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        with self._state_lock:
            keys_to_remove = [k for k in self._state.keys() if k < cutoff]
            for k in keys_to_remove:
                del self._state[k]
            
            if keys_to_remove:
                self._save_state()


rate_limiter = EmailRateLimiter()


class Notifier:
    """通知发送器"""
    
    def __init__(
        self,
        smtp_host: str = '',
        smtp_port: int = 587,
        smtp_user: str = '',
        smtp_password: str = '',
        notification_email: str = '',
        webhook_url: str = '',
        max_daily_emails: int = 10,
    ):
        """
        初始化通知器
        
        Args:
            smtp_host: SMTP服务器地址
            smtp_port: SMTP端口
            smtp_user: SMTP用户名
            smtp_password: SMTP密码
            notification_email: 接收通知的邮箱
            webhook_url: Webhook URL（支持企业微信、钉钉、飞书等）
            max_daily_emails: 每日最大邮件发送数量，0表示不限制
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.notification_email = notification_email
        self.webhook_url = webhook_url
        self.max_daily_emails = max_daily_emails
    
    def send_notification(
        self,
        title: str,
        results: List[Dict[str, Any]],
        summary: Dict[str, int],
    ) -> bool:
        """
        发送通知
        
        Args:
            title: 通知标题
            results: 执行结果列表
            summary: 执行摘要 {'total': x, 'success': y, 'fail': z}
            
        Returns:
            是否发送成功
        """
        success_count = summary.get('success', 0)
        fail_count = summary.get('fail', 0)
        
        if fail_count == 0:
            logger.info('所有账号延期成功，不发送通知')
            return True
        
        content = self._format_content(title, results, summary)
        
        sent = False
        
        if self.notification_email and self.smtp_host:
            if self._send_email(title, content):
                sent = True
        
        if self.webhook_url:
            if self._send_webhook(title, content, summary):
                sent = True
        
        if not sent and fail_count > 0:
            logger.warning('未配置通知渠道，无法发送失败通知')
        
        return sent
    
    def send_verification_failed_notification(
        self,
        title: str,
        results: List[Dict[str, Any]],
        summary: Dict[str, int],
    ) -> bool:
        """
        发送验证失败通知（延期未生效，需要手动处理）
        
        实现说明:
        1. 验证失败意味着上次延期申请未真正生效
        2. 程序已自动重新提交延期，但仍需通知用户关注
        3. 邮件内容强调需要用户手动确认
        
        Args:
            title: 通知标题
            results: 验证失败账号列表
            summary: 执行摘要
            
        Returns:
            是否发送成功
        """
        content = self._format_verification_failed_content(title, results, summary)
        
        sent = False
        
        if self.notification_email and self.smtp_host:
            if self._send_email(title, content, urgent=True):
                sent = True
        
        if self.webhook_url:
            if self._send_webhook(title, content, summary):
                sent = True
        
        if not sent:
            logger.warning('未配置通知渠道，无法发送验证失败通知')
        
        return sent
    
    def _format_content(
        self,
        title: str,
        results: List[Dict[str, Any]],
        summary: Dict[str, int],
    ) -> str:
        """格式化通知内容"""
        lines = [
            f"【{title}】",
            f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"执行摘要:",
            f"  总计: {summary.get('total', 0)} 个账号",
            f"  成功: {summary.get('success', 0)} 个",
            f"  失败: {summary.get('fail', 0)} 个",
            "",
        ]
        
        fail_results = [r for r in results if not r.get('success', False)]
        if fail_results:
            lines.append("失败详情:")
            for result in fail_results:
                platform = result.get('platform', 'unknown')
                lines.append(f"  - [{platform}] {result.get('username', 'unknown')}: {result.get('message', '未知错误')}")
        
        return '\n'.join(lines)
    
    def _format_verification_failed_content(
        self,
        title: str,
        results: List[Dict[str, Any]],
        summary: Dict[str, int],
    ) -> str:
        """格式化验证失败通知内容"""
        lines = [
            f"【重要】{title}",
            f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=" * 50,
            "警告：以下账号的延期申请未真正生效！",
            "=" * 50,
            "",
            "程序已自动重新提交延期申请，但请您手动登录确认：",
            "",
        ]
        
        for result in results:
            platform = result.get('platform', 'unknown')
            username = result.get('username', 'unknown')
            message = result.get('message', '未知')
            lines.append(f"  平台: {platform}")
            lines.append(f"  账号: {username}")
            lines.append(f"  状态: {message}")
            lines.append("")
        
        lines.extend([
            "=" * 50,
            "请尽快登录平台确认延期状态！",
            "=" * 50,
            "",
            "可能的原因：",
            "1. 截图不符合要求",
            "2. 发帖链接无效",
            "3. 平台审核未通过",
            "4. 网络问题导致提交失败",
            "",
            "建议操作：",
            "1. 登录平台查看延期记录",
            "2. 检查截图和发帖链接是否正确",
            "3. 如有问题，手动重新提交延期",
        ])
        
        return '\n'.join(lines)
    
    def _send_email(self, subject: str, content: str, urgent: bool = False) -> bool:
        """发送邮件通知"""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.notification_email]):
            logger.warning('邮件通知配置不完整，跳过发送')
            return False
        
        if not rate_limiter.can_send(self.max_daily_emails):
            today_count = rate_limiter.get_today_count()
            logger.warning(f'已达到每日邮件发送上限 ({today_count}/{self.max_daily_emails})，跳过发送')
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.notification_email
            
            if urgent:
                msg['Subject'] = f"[重要-需处理] 云主机延期验证失败 - {subject}"
                msg['Priority'] = 'high'
            else:
                msg['Subject'] = f"[云主机延期] {subject}"
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, self.notification_email, msg.as_string())
            
            rate_limiter.record_send()
            rate_limiter.cleanup_old_records()
            
            today_count = rate_limiter.get_today_count()
            logger.info(f'邮件通知已发送到 {self.notification_email} (今日已发送: {today_count}/{self.max_daily_emails})')
            return True
            
        except Exception as e:
            logger.error(f'发送邮件通知失败: {e}')
            return False
    
    def _send_webhook(
        self,
        title: str,
        content: str,
        summary: Dict[str, int],
    ) -> bool:
        """发送Webhook通知"""
        if not self.webhook_url:
            return False
        
        try:
            import requests
            
            webhook_data = self._format_webhook_data(title, content, summary)
            
            resp = requests.post(
                self.webhook_url,
                json=webhook_data,
                timeout=10,
            )
            
            if resp.status_code == 200:
                logger.info('Webhook通知已发送')
                return True
            else:
                logger.error(f'Webhook通知发送失败: HTTP {resp.status_code}')
                return False
                
        except Exception as e:
            logger.error(f'发送Webhook通知失败: {e}')
            return False
    
    def _format_webhook_data(
        self,
        title: str,
        content: str,
        summary: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        格式化Webhook数据
        
        支持格式:
        - 企业微信/钉钉: {"msgtype": "text", "text": {"content": "..."}}
        - 飞书: {"msg_type": "text", "content": {"text": "..."}}
        - 自定义: 直接发送summary
        """
        fail_count = summary.get('fail', 0)
        status = "失败" if fail_count > 0 else "成功"
        
        return {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }


def create_notifier_from_config() -> Notifier:
    """从配置创建通知器"""
    from src.config import config
    
    return Notifier(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        notification_email=config.notification_email,
        webhook_url=getattr(config, 'webhook_url', ''),
        max_daily_emails=getattr(config, 'max_daily_emails', 10),
    )
