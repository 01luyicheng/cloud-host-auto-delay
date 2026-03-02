"""
账号延期状态管理模块

文件用途: 管理每个账号的延期状态，包括上次延期时间、下次计划时间等
创建日期: 2026-02-22
更新日期: 2026-02-22
输入: 账号延期记录
输出: 延期状态、下次执行时间
依赖: 无外部依赖

实现说明:
1. 使用单例模式管理状态
2. 状态持久化到JSON文件
3. 支持账号级别的延期间隔配置
4. 线程安全的操作
5. 支持失败重试和指数退避
6. 启动时检查错过的延期任务
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.logger import logger


class AccountDelayState:
    """单个账号的延期状态"""
    
    def __init__(self, data: Dict[str, Any] = None):
        data = data or {}
        self.last_delay_time: Optional[datetime] = None
        if data.get('last_delay_time'):
            try:
                self.last_delay_time = datetime.fromisoformat(data['last_delay_time'])
            except (ValueError, TypeError):
                self.last_delay_time = None
        
        self.next_delay_time: Optional[datetime] = None
        if data.get('next_delay_time'):
            try:
                self.next_delay_time = datetime.fromisoformat(data['next_delay_time'])
            except (ValueError, TypeError):
                self.next_delay_time = None
        
        self.last_success: bool = data.get('last_success', False)
        self.last_message: str = data.get('last_message', '')
        self.delay_count: int = data.get('delay_count', 0)
        self.consecutive_failures: int = data.get('consecutive_failures', 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'last_delay_time': self.last_delay_time.isoformat() if self.last_delay_time else None,
            'next_delay_time': self.next_delay_time.isoformat() if self.next_delay_time else None,
            'last_success': self.last_success,
            'last_message': self.last_message,
            'delay_count': self.delay_count,
            'consecutive_failures': self.consecutive_failures,
        }


class AccountStateManager:
    """账号状态管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    MAX_RETRY_HOURS = 24
    MAX_CONSECUTIVE_FAILURES = 10
    
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
        self._states: Dict[str, AccountDelayState] = {}
        self._file_lock = threading.Lock()
        
        self.state_file = Path(__file__).parent.parent / 'data' / 'account_state.json'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_states()
    
    def _get_state_key(self, platform: str, username: str) -> str:
        """获取状态键"""
        return f"{platform}:{username}"
    
    def _load_states(self):
        """加载状态文件"""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, state_data in data.items():
                self._states[key] = AccountDelayState(state_data)
            
            logger.info(f'加载账号状态: {len(self._states)} 个账号')
        except Exception as e:
            logger.error(f'加载账号状态失败: {e}')
    
    def _save_states(self):
        """保存状态文件"""
        try:
            data = {key: state.to_dict() for key, state in self._states.items()}
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f'保存账号状态失败: {e}')
    
    def get_state(self, platform: str, username: str) -> AccountDelayState:
        """获取账号状态"""
        with self._file_lock:
            key = self._get_state_key(platform, username)
            if key not in self._states:
                self._states[key] = AccountDelayState()
            return self._states[key]
    
    def _calculate_retry_delay(self, consecutive_failures: int) -> timedelta:
        """
        计算重试延迟（指数退避）
        
        实现说明:
        1. 第1次失败: 1小时后重试
        2. 第2次失败: 2小时后重试
        3. 第3次失败: 4小时后重试
        4. 第4次失败: 8小时后重试
        5. 第5次及以后: 16小时后重试（最大）
        """
        if consecutive_failures <= 0:
            return timedelta(hours=1)
        
        hours = min(2 ** (consecutive_failures - 1), 16)
        return timedelta(hours=hours)
    
    def record_delay(
        self,
        platform: str,
        username: str,
        success: bool,
        message: str,
        delay_interval_days: int = 5,
    ):
        """
        记录延期结果
        
        Args:
            platform: 平台
            username: 用户名
            success: 是否成功
            message: 结果消息
            delay_interval_days: 延期间隔天数
        """
        with self._file_lock:
            key = self._get_state_key(platform, username)
            state = self.get_state(platform, username)
            
            state.last_delay_time = datetime.now()
            state.last_success = success
            state.last_message = message
            
            if success:
                state.delay_count += 1
                state.consecutive_failures = 0
                state.next_delay_time = datetime.now() + timedelta(days=delay_interval_days)
            else:
                state.consecutive_failures += 1
                retry_delay = self._calculate_retry_delay(state.consecutive_failures)
                state.next_delay_time = datetime.now() + retry_delay
                
                if state.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    logger.error(f'账号 [{platform}] {username} 连续失败 {state.consecutive_failures} 次，已达到最大重试次数')
            
            self._states[key] = state
            self._save_states()
            
            logger.info(f'记录账号状态: [{platform}] {username}, 成功={success}, 连续失败={state.consecutive_failures}, 下次延期={state.next_delay_time}')
    
    def record_aggressive_mode_delay(
        self,
        platform: str,
        username: str,
        aggressive_interval_hours: int = 6,
    ):
        """
        记录高频尝试模式下的延期状态
        
        实现说明:
        1. 当高频模式下尝试延期但"还未到时间"时调用
        2. 不增加失败计数，使用高频间隔设置下次尝试时间
        3. 重置连续失败计数（因为这是预期内的"失败"）
        
        Args:
            platform: 平台
            username: 用户名
            aggressive_interval_hours: 高频尝试间隔小时数
        """
        with self._file_lock:
            key = self._get_state_key(platform, username)
            state = self.get_state(platform, username)
            
            state.last_delay_time = datetime.now()
            state.last_success = True  # 在高频模式下，"还未到时间"视为正常情况
            state.last_message = '高频模式：还未到可延期时间，等待下次尝试'
            state.consecutive_failures = 0  # 重置失败计数
            state.next_delay_time = datetime.now() + timedelta(hours=aggressive_interval_hours)
            
            self._states[key] = state
            self._save_states()
            
            logger.info(f'记录高频模式状态: [{platform}] {username}, 下次尝试={state.next_delay_time}')
    
    def set_initial_next_delay_time(
        self,
        platform: str,
        username: str,
        first_delay_days: int,
    ):
        """
        设置初始下次延期时间
        
        Args:
            platform: 平台
            username: 用户名
            first_delay_days: 首次延期天数（从现在开始计算）
        """
        with self._file_lock:
            key = self._get_state_key(platform, username)
            state = self.get_state(platform, username)
            
            if state.next_delay_time is None:
                state.next_delay_time = datetime.now() + timedelta(days=first_delay_days)
                self._states[key] = state
                self._save_states()
                logger.info(f'设置初始延期时间: [{platform}] {username}, 首次延期={first_delay_days}天后')
    
    def should_delay(self, platform: str, username: str) -> bool:
        """
        检查是否应该执行延期
        
        Args:
            platform: 平台
            username: 用户名
            
        Returns:
            是否应该执行延期
        """
        state = self.get_state(platform, username)
        
        if state.next_delay_time is None:
            return True
        
        return datetime.now() >= state.next_delay_time
    
    def get_next_delay_time(self, platform: str, username: str) -> Optional[datetime]:
        """获取下次延期时间"""
        state = self.get_state(platform, username)
        return state.next_delay_time
    
    def get_consecutive_failures(self, platform: str, username: str) -> int:
        """获取连续失败次数"""
        state = self.get_state(platform, username)
        return state.consecutive_failures
    
    def is_max_retries_exceeded(self, platform: str, username: str) -> bool:
        """检查是否已超过最大重试次数"""
        state = self.get_state(platform, username)
        return state.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES
    
    def get_all_pending_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有待执行延期的账号
        
        Returns:
            待执行账号列表，每个元素包含 platform, username, next_delay_time
        """
        pending = []
        now = datetime.now()
        
        for key, state in self._states.items():
            if state.next_delay_time and state.next_delay_time <= now:
                platform, username = key.split(':', 1)
                pending.append({
                    'platform': platform,
                    'username': username,
                    'next_delay_time': state.next_delay_time,
                    'consecutive_failures': state.consecutive_failures,
                })
        
        return pending
    
    def get_missed_accounts(self) -> List[Dict[str, Any]]:
        """
        获取错过的延期任务（启动时检查）
        
        实现说明:
        1. 检查 next_delay_time 已经过期的账号
        2. 排除已达到最大重试次数的账号
        """
        missed = []
        now = datetime.now()
        
        for key, state in self._states.items():
            if state.next_delay_time and state.next_delay_time < now:
                if state.consecutive_failures < self.MAX_CONSECUTIVE_FAILURES:
                    platform, username = key.split(':', 1)
                    overdue_hours = (now - state.next_delay_time).total_seconds() / 3600
                    missed.append({
                        'platform': platform,
                        'username': username,
                        'next_delay_time': state.next_delay_time,
                        'overdue_hours': overdue_hours,
                        'consecutive_failures': state.consecutive_failures,
                    })
        
        return missed
    
    def reset_failures(self, platform: str, username: str):
        """重置连续失败计数"""
        with self._file_lock:
            key = self._get_state_key(platform, username)
            state = self.get_state(platform, username)
            state.consecutive_failures = 0
            self._states[key] = state
            self._save_states()
    
    def clear_old_states(self, days: int = 30):
        """清理旧状态（保留最近N天有活动的账号）"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._file_lock:
            keys_to_remove = []
            for key, state in self._states.items():
                if state.last_delay_time and state.last_delay_time < cutoff:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._states[key]
            
            if keys_to_remove:
                self._save_states()
                logger.info(f'清理旧账号状态: {len(keys_to_remove)} 个')


account_state_manager = AccountStateManager()
