"""
延期状态管理模块

文件用途: 管理延期提交的状态追踪和验证
创建日期: 2026-02-22
输入: 账号信息、延期提交结果
输出: 延期状态、验证结果
依赖: 无

实现说明:
1. 记录每次延期提交的时间和结果
2. 5小时后验证延期是否真正成功
3. 验证方法：再次提交延期，如果成功说明上次失败
4. 状态持久化到JSON文件，程序重启后可恢复
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from threading import Lock

from src.logger import logger


class DelayStatus:
    """延期状态枚举"""
    PENDING = 'pending'          # 待提交
    SUBMITTED = 'submitted'      # 已提交，待验证
    VERIFIED = 'verified'        # 已验证成功
    FAILED = 'failed'            # 验证失败（需要手动处理）


class DelayStateManager:
    """
    延期状态管理器
    
    实现说明:
    1. 使用单例模式管理状态
    2. 状态持久化到JSON文件
    3. 线程安全的状态更新
    4. 支持状态查询和更新
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
        self.state_file = self.project_root / 'data' / 'delay_state.json'
        self.state_file.parent.mkdir(exist_ok=True)
        
        self._load_state()
    
    def _load_state(self):
        """加载状态文件"""
        with self._state_lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        self._state: Dict[str, Dict[str, Any]] = json.load(f)
                    logger.debug(f'延期状态已加载: {len(self._state)} 条记录')
                except Exception as e:
                    logger.error(f'加载延期状态失败: {e}')
                    self._state = {}
            else:
                self._state = {}
    
    def _save_state(self):
        """保存状态文件"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f'保存延期状态失败: {e}')
    
    def _get_account_key(self, platform: str, username: str) -> str:
        """生成账号唯一标识"""
        return f'{platform}:{username}'
    
    def record_submission(
        self,
        platform: str,
        username: str,
        ptype: str,
        post_url: str,
        screenshot_path: str,
        success: bool,
        message: str,
        verification_delay_hours: int = 5,
    ):
        """
        记录延期提交
        
        Args:
            platform: 平台名称
            username: 用户名
            ptype: 产品类型
            post_url: 发帖地址
            screenshot_path: 截图路径
            success: 是否成功
            message: 返回消息
            verification_delay_hours: 验证延迟小时数
        """
        key = self._get_account_key(platform, username)
        now = datetime.now()
        verify_time = now + timedelta(hours=verification_delay_hours)
        
        with self._state_lock:
            self._state[key] = {
                'platform': platform,
                'username': username,
                'ptype': ptype,
                'post_url': post_url,
                'screenshot_path': screenshot_path,
                'status': DelayStatus.SUBMITTED if success else DelayStatus.FAILED,
                'submit_time': now.isoformat(),
                'verify_time': verify_time.isoformat(),
                'submit_message': message,
                'verify_attempted': False,
                'verify_success': None,
                'verify_message': None,
            }
            self._save_state()
        
        if success:
            logger.info(f'[{platform}] {username} 延期已提交，将在 {verify_time.strftime("%H:%M")} 验证')
        else:
            logger.warning(f'[{platform}] {username} 延期提交失败: {message}')
    
    def get_pending_verifications(self) -> List[Dict[str, Any]]:
        """
        获取待验证的账号列表
        
        Returns:
            待验证账号列表，每个元素包含账号信息和验证时间
        """
        now = datetime.now()
        pending = []
        
        with self._state_lock:
            for key, state in self._state.items():
                if state.get('status') != DelayStatus.SUBMITTED:
                    continue
                
                verify_time_str = state.get('verify_time')
                if not verify_time_str:
                    continue
                
                try:
                    verify_time = datetime.fromisoformat(verify_time_str)
                    if now >= verify_time and not state.get('verify_attempted'):
                        pending.append(state.copy())
                except Exception as e:
                    logger.error(f'解析验证时间失败: {e}')
        
        return pending
    
    def record_verification(
        self,
        platform: str,
        username: str,
        verify_success: bool,
        verify_message: str,
    ):
        """
        记录验证结果
        
        实现说明:
        1. 如果验证时再次提交成功，说明上次延期失败
        2. 如果验证时提交失败（已提交过），说明上次延期成功
        
        Args:
            platform: 平台名称
            username: 用户名
            verify_success: 验证提交是否成功
            verify_message: 验证返回消息
        """
        key = self._get_account_key(platform, username)
        
        with self._state_lock:
            if key not in self._state:
                logger.warning(f'未找到延期状态记录: {key}')
                return
            
            state = self._state[key]
            state['verify_attempted'] = True
            state['verify_success'] = verify_success
            state['verify_message'] = verify_message
            
            if verify_success:
                state['status'] = DelayStatus.FAILED
                logger.warning(f'[{platform}] {username} 延期验证失败：上次延期未成功，需要手动处理')
            else:
                state['status'] = DelayStatus.VERIFIED
                logger.info(f'[{platform}] {username} 延期验证成功：上次延期已生效')
            
            self._save_state()
    
    def get_failed_accounts(self) -> List[Dict[str, Any]]:
        """
        获取验证失败的账号列表（需要手动处理）
        
        Returns:
            失败账号列表
        """
        failed = []
        
        with self._state_lock:
            for key, state in self._state.items():
                if state.get('status') == DelayStatus.FAILED:
                    failed.append(state.copy())
        
        return failed
    
    def get_status(self, platform: str, username: str) -> Optional[Dict[str, Any]]:
        """获取指定账号的延期状态"""
        key = self._get_account_key(platform, username)
        with self._state_lock:
            return self._state.get(key, {}).copy()
    
    def clear_old_states(self, days: int = 7):
        """
        清理旧状态记录
        
        Args:
            days: 保留天数
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleared = 0
        
        with self._state_lock:
            keys_to_remove = []
            for key, state in self._state.items():
                submit_time_str = state.get('submit_time')
                if submit_time_str:
                    try:
                        submit_time = datetime.fromisoformat(submit_time_str)
                        if submit_time < cutoff:
                            keys_to_remove.append(key)
                    except Exception:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._state[key]
                cleared += 1
            
            if cleared > 0:
                self._save_state()
                logger.info(f'已清理 {cleared} 条过期延期状态记录')


state_manager = DelayStateManager()
