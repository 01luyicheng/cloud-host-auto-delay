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


class LearningModeStatus:
    """学习模式状态枚举"""
    NOT_STARTED = 'not_started'    # 未开始（首次运行）
    LEARNING = 'learning'          # 学习中（高频尝试找时间点）
    LEARNED = 'learned'            # 已学习（找到规律，进入固定周期）


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
        
        # 学习模式相关字段
        self.learning_status: str = data.get('learning_status', LearningModeStatus.NOT_STARTED)
        self.learned_delay_time: Optional[datetime] = None  # 学习到的最佳提交时间
        if data.get('learned_delay_time'):
            try:
                self.learned_delay_time = datetime.fromisoformat(data['learned_delay_time'])
            except (ValueError, TypeError):
                self.learned_delay_time = None
        self.learning_start_time: Optional[datetime] = None  # 学习开始时间
        if data.get('learning_start_time'):
            try:
                self.learning_start_time = datetime.fromisoformat(data['learning_start_time'])
            except (ValueError, TypeError):
                self.learning_start_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'last_delay_time': self.last_delay_time.isoformat() if self.last_delay_time else None,
            'next_delay_time': self.next_delay_time.isoformat() if self.next_delay_time else None,
            'last_success': self.last_success,
            'last_message': self.last_message,
            'delay_count': self.delay_count,
            'consecutive_failures': self.consecutive_failures,
            'learning_status': self.learning_status,
            'learned_delay_time': self.learned_delay_time.isoformat() if self.learned_delay_time else None,
            'learning_start_time': self.learning_start_time.isoformat() if self.learning_start_time else None,
        }


class AccountStateManager:
    """账号状态管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    MAX_CONSECUTIVE_FAILURES = 10
    LEARNING_TIMEOUT_DAYS = 7
    
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
        self._file_lock = threading.RLock()  # 使用可重入锁避免死锁
        
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
        """保存状态文件（原子写入）"""
        try:
            data = {key: state.to_dict() for key, state in self._states.items()}
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.state_file)  # 原子操作
        except Exception as e:
            logger.error(f'保存账号状态失败: {e}')
    
    def _get_or_create_state(self, platform: str, username: str) -> AccountDelayState:
        """
        获取或创建账号状态（内部方法，不返回副本）
        
        实现说明:
        1. 该方法必须在持有 _file_lock 的情况下调用
        2. 返回内部状态的引用，用于直接修改
        3. 外部调用者应使用 get_state() 获取副本
        
        Args:
            platform: 平台
            username: 用户名
            
        Returns:
            账号状态对象（内部引用）
        """
        key = self._get_state_key(platform, username)
        if key not in self._states:
            self._states[key] = AccountDelayState()
        return self._states[key]
    
    def get_state(self, platform: str, username: str) -> AccountDelayState:
        """
        获取账号状态（返回副本，避免调用者直接修改内部状态）
        
        实现说明:
        1. 返回状态的深拷贝，防止并发访问时的数据竞争
        2. 调用者可以安全地修改返回的状态对象
        """
        with self._file_lock:
            state = self._get_or_create_state(platform, username)
            return AccountDelayState(state.to_dict())
    
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
            state = self._get_or_create_state(platform, username)
            
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
            
            self._save_states()
            
            logger.info(f'记录账号状态：[{platform}] {username}, 成功={success}, 连续失败={state.consecutive_failures}, 下次延期={state.next_delay_time}')
    
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
            state = self._get_or_create_state(platform, username)
            
            state.last_delay_time = datetime.now()
            state.last_success = True  # 在高频模式下，"还未到时间"视为正常情况
            state.last_message = '高频模式：还未到可延期时间，等待下次尝试'
            state.consecutive_failures = 0  # 重置失败计数
            state.next_delay_time = datetime.now() + timedelta(hours=aggressive_interval_hours)
            
            self._save_states()
            
            logger.info(f'记录高频模式状态：[{platform}] {username}, 下次尝试={state.next_delay_time}')
    
    def start_learning_mode(
        self,
        platform: str,
        username: str,
        learning_interval_hours: int = 2,
    ) -> bool:
        """
        启动学习模式
        
        实现说明:
        1. 首次运行时自动进入学习模式
        2. 高频尝试提交，找到"刚开始允许提交"的时间点
        3. 学习模式最长持续7天
        
        Args:
            platform: 平台
            username: 用户名
            learning_interval_hours: 学习阶段尝试间隔（默认2小时）
            
        Returns:
            是否成功启动学习模式
        """
        with self._file_lock:
            state = self._get_or_create_state(platform, username)
            
            # 如果已经在学习中或已学习，不重复启动
            if state.learning_status == LearningModeStatus.LEARNING:
                return False
            if state.learning_status == LearningModeStatus.LEARNED:
                return False
            
            state.learning_status = LearningModeStatus.LEARNING
            state.learning_start_time = datetime.now()
            state.next_delay_time = datetime.now()  # 立即开始第一次尝试
            
            self._save_states()
            
            logger.info(f'【学习模式】启动: [{platform}] {username}，将高频尝试找到最佳提交时间')
            return True
    
    def record_learning_attempt(
        self,
        platform: str,
        username: str,
        success: bool,
        message: str,
        learning_interval_hours: int = 2,
        delay_interval_days: int = 5,
    ) -> bool:
        """
        记录学习模式的尝试结果
        
        实现说明:
        1. 如果提交成功，说明找到了最佳时间点，进入已学习状态
        2. 如果提交失败（还未到时间），继续学习，按间隔重试
        3. 学习超过7天仍未成功，则放弃学习，按配置的时间提交
        
        Args:
            platform: 平台
            username: 用户名
            success: 是否成功
            message: 结果消息
            learning_interval_hours: 学习间隔小时数
            delay_interval_days: 延期间隔天数
            
        Returns:
            是否已完成学习（找到最佳时间点）
        """
        with self._file_lock:
            state = self._get_or_create_state(platform, username)
            
            # 检查是否在学习中
            if state.learning_status != LearningModeStatus.LEARNING:
                return False
            
            now = datetime.now()
            state.last_delay_time = now
            state.last_message = message
            
            # 检查学习是否超时（使用精确时间比较）
            if state.learning_start_time:
                learning_duration = now - state.learning_start_time
                if learning_duration.total_seconds() >= self.LEARNING_TIMEOUT_DAYS * 24 * 3600:
                    logger.warning(f'【学习模式】超时: [{platform}] {username} 学习超过{self.LEARNING_TIMEOUT_DAYS}天仍未找到最佳时间，放弃学习')
                    state.learning_status = LearningModeStatus.NOT_STARTED
                    state.next_delay_time = now + timedelta(days=delay_interval_days)  # 使用默认配置
                    self._save_states()
                    return False
            
            if success:
                # 找到了！记录这个时间点
                state.learning_status = LearningModeStatus.LEARNED
                state.learned_delay_time = now
                state.last_success = True
                state.delay_count += 1
                state.consecutive_failures = 0
                # 设置下次延期时间
                state.next_delay_time = now + timedelta(days=delay_interval_days)
                
                self._save_states()
                
                logger.info(f'【学习模式】完成: [{platform}] {username} 找到最佳提交时间: {now.strftime("%Y-%m-%d %H:%M")}')
                return True
            else:
                # 还未到时间，继续学习
                state.last_success = False
                state.next_delay_time = now + timedelta(hours=learning_interval_hours)
                
                self._save_states()
                
                logger.info(f'【学习模式】继续：[{platform}] {username} 还未到时间，下次尝试={state.next_delay_time}')
                return False
    
    def is_in_learning_mode(self, platform: str, username: str) -> bool:
        """检查账号是否处于学习模式"""
        state = self.get_state(platform, username)
        return state.learning_status == LearningModeStatus.LEARNING
    
    def has_learned(self, platform: str, username: str) -> bool:
        """检查账号是否已完成学习"""
        state = self.get_state(platform, username)
        return state.learning_status == LearningModeStatus.LEARNED
    
    def get_learned_time(self, platform: str, username: str) -> Optional[datetime]:
        """获取学习到的最佳提交时间"""
        state = self.get_state(platform, username)
        return state.learned_delay_time
    
    def calculate_next_delay_from_learned_time(
        self,
        platform: str,
        username: str,
        delay_interval_days: int,
    ) -> Optional[datetime]:
        """
        根据学习到的最佳时间计算下次延期时间
        
        实现说明:
        1. 如果已完成学习，根据学习到的最佳时间 + 固定周期计算
        2. 保持每天的时间点一致（例如每天14:30）
        
        Args:
            platform: 平台
            username: 用户名
            delay_interval_days: 延期间隔天数
            
        Returns:
            下次延期时间，如果未学习则返回None
        """
        state = self.get_state(platform, username)
        
        if state.learning_status != LearningModeStatus.LEARNED or not state.learned_delay_time:
            return None
        
        learned_time = state.learned_delay_time
        now = datetime.now()
        
        # 使用精确时间计算（total_seconds）而不是只取天数
        seconds_since_learned = (now - learned_time).total_seconds()
        days_since_learned = seconds_since_learned / (24 * 3600)
        cycles_passed = int(days_since_learned // delay_interval_days)
        
        # 下次延期时间 = 学习时间 + (周期数+1) * 间隔
        next_delay = learned_time + timedelta(days=(cycles_passed + 1) * delay_interval_days)
        
        return next_delay
    
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
            state = self._get_or_create_state(platform, username)
            
            if state.next_delay_time is None:
                state.next_delay_time = datetime.now() + timedelta(days=first_delay_days)
                self._save_states()
                logger.info(f'设置初始延期时间：[{platform}] {username}, 首次延期={first_delay_days}天后')
    
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
            state = self._get_or_create_state(platform, username)
            state.consecutive_failures = 0
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
