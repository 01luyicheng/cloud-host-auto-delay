"""
配置文件管理模块

文件用途: 管理程序配置，包括账号信息、环境变量等
创建日期: 2026-02-17
更新日期: 2026-02-18
输入: 配置文件路径、环境变量
输出: 配置对象
依赖: python-dotenv>=1.0.0

实现说明:
1. 使用单例模式管理配置
2. 敏感信息从环境变量读取
3. 账号配置从JSON文件读取
4. 支持多账号管理
5. 线程安全的单例实现
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


class AccountConfig:
    """单个账号配置"""
    
    def __init__(self, data: Dict[str, Any]):
        self.username: str = data.get('username', '')
        self.password: str = data.get('password', '')
        self.platform: str = data.get('platform', 'abeiyun').lower()  # 平台：abeiyun或sanfengyun
        self.post_url: str = data.get('post_url', '')
        self.screenshot_path: str = data.get('screenshot_path', '')
        self.ptype: str = data.get('ptype', 'vps')  # 产品类型：vps或vhost
        self.enabled: bool = data.get('enabled', True)
        
        self.schedule_hour: int = data.get('schedule_hour', 2)
        self.schedule_minute: int = data.get('schedule_minute', 0)
        
        self.first_delay_days: int = data.get('first_delay_days', 0)
        self.delay_interval_days: int = data.get('delay_interval_days', 5)
    
    def validate(self) -> Tuple[bool, str]:
        """验证账号配置是否完整"""
        if not self.username:
            return False, '用户名不能为空'
        if not self.password:
            return False, '密码不能为空'
        if not self.post_url:
            return False, '发帖地址不能为空'
        if not self.screenshot_path:
            return False, '截图路径不能为空'
        if not os.path.exists(self.screenshot_path):
            return False, f'截图文件不存在: {self.screenshot_path}'
        if self.platform not in ('abeiyun', 'sanfengyun'):
            return False, f'不支持的平台: {self.platform}'
        if self.ptype not in ('vps', 'vhost'):
            return False, f'不支持的产品类型: {self.ptype}'
        if self.first_delay_days < 0:
            return False, '首次延期天数不能为负数'
        if self.delay_interval_days < 1:
            return False, '延期间隔天数必须大于0'
        return True, ''


class Config:
    """全局配置管理"""
    
    _instance = None
    _lock = threading.Lock()
    
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
        self._load_config()
    
    def _load_config(self):
        """加载所有配置"""
        # 项目根目录
        self.project_root = Path(__file__).parent.parent
        
        # 日志配置（必须在加载账号配置之前初始化logger）
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_dir = self.project_root / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # 初始化logger（延迟导入避免循环依赖）
        from src.logger import setup_logger
        self.logger = setup_logger(log_dir=self.log_dir, log_level=self.log_level)
        
        # 加载账号配置
        self.accounts: List[AccountConfig] = self._load_accounts()
        
        # SMTP配置
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL', '')
        
        # Webhook通知配置（支持企业微信、钉钉、飞书等）
        self.webhook_url = os.getenv('WEBHOOK_URL', '')
        
        # 延期验证配置
        self.verification_delay_hours = int(os.getenv('VERIFICATION_DELAY_HOURS', '5'))
        
        # 邮件发送限制
        self.max_daily_emails = int(os.getenv('MAX_DAILY_EMAILS', '10'))
    
    def _load_accounts(self) -> List[AccountConfig]:
        """
        加载账号配置
        
        实现说明:
        1. 支持全局配置（global），账号可继承
        2. 账号级别配置优先于全局配置
        3. 将相对路径转换为绝对路径
        """
        accounts_file = self.project_root / 'config' / 'accounts.json'
        
        if not accounts_file.exists():
            example_file = self.project_root / 'config' / 'accounts.example.json'
            if example_file.exists():
                self.logger.warning(f'未找到账号配置文件，请复制 {example_file} 为 {accounts_file} 并填写真实信息')
            else:
                self.logger.warning(f'未找到账号配置文件: {accounts_file}')
            return []
        
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            global_config = data.get('global', {})
            
            accounts = []
            for account_data in data.get('accounts', []):
                merged_data = {
                    'platform': account_data.get('platform') or global_config.get('platform', 'abeiyun'),
                    'post_url': account_data.get('post_url') or global_config.get('post_url', ''),
                    'screenshot_path': account_data.get('screenshot_path') or global_config.get('screenshot_path', ''),
                    'schedule_hour': account_data.get('schedule_hour', global_config.get('schedule_hour', 2)),
                    'schedule_minute': account_data.get('schedule_minute', global_config.get('schedule_minute', 0)),
                    'ptype': account_data.get('ptype', global_config.get('ptype', 'vps')),
                    'first_delay_days': account_data.get('first_delay_days', global_config.get('first_delay_days', 0)),
                    'delay_interval_days': account_data.get('delay_interval_days', global_config.get('delay_interval_days', 5)),
                }
                merged_data.update(account_data)
                
                screenshot_path = merged_data.get('screenshot_path', '')
                if screenshot_path and not Path(screenshot_path).is_absolute():
                    merged_data['screenshot_path'] = str(self.project_root / screenshot_path)
                
                account = AccountConfig(merged_data)
                valid, msg = account.validate()
                if valid:
                    accounts.append(account)
                else:
                    self.logger.warning(f'账号 {account.username} 配置无效: {msg}')
            
            return accounts
        except json.JSONDecodeError as e:
            self.logger.error(f'账号配置文件格式错误: {e}')
            return []
        except Exception as e:
            self.logger.error(f'加载账号配置失败: {e}')
            return []
    
    def get_enabled_accounts(self) -> List[AccountConfig]:
        """获取启用的账号列表"""
        return [acc for acc in self.accounts if acc.enabled]
    
    def reload(self):
        """重新加载配置"""
        self._load_config()


# 全局配置实例
config = Config()
