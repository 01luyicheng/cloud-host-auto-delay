"""
定时任务调度模块

文件用途: 管理延期任务的定时执行和验证
创建日期: 2026-02-17
更新日期: 2026-02-22
输入: 调度配置（执行时间）
输出: 定时触发的延期任务
依赖: APScheduler>=3.10.4

实现说明:
1. 使用APScheduler实现定时任务
2. 支持账号级别的首次延期天数和延期间隔天数
3. 每小时检查一次所有账号是否需要延期
4. 每个账号独立执行，互不影响
5. 支持失败通知（邮件/Webhook）
6. 延期提交5小时后自动验证
7. 验证失败时发送邮件通知
8. 使用锁机制确保多账号并发安全
9. 启动时检查错过的延期任务
10. 失败重试使用指数退避
11. 连续失败达到阈值时发送警告通知
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import config, AccountConfig
from src.logger import logger
from src.cloud_client import create_client
from src.notifier import create_notifier_from_config
from src.delay_state import state_manager, DelayStatus
from src.account_state import account_state_manager


class DelayScheduler:
    """延期任务调度器"""
    
    FAILURE_WARNING_THRESHOLD = 3
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler = BackgroundScheduler()
        self._running_accounts = set()
        self._account_lock = threading.Lock()
        self._setup_jobs()
        self._setup_verification_job()
    
    def _setup_jobs(self):
        """
        配置定时任务
        
        实现说明:
        1. 每小时检查一次所有账号是否需要延期
        2. 初始化账号的首次延期时间
        """
        trigger = IntervalTrigger(hours=1)
        
        self.scheduler.add_job(
            self._check_and_run_delay_tasks,
            trigger=trigger,
            id='delay_check_task',
            name='延期检查任务',
            replace_existing=True,
        )
        
        self._init_account_delay_times()
        
        logger.info('定时任务已配置: 每小时检查一次是否需要延期')
    
    def _init_account_delay_times(self):
        """
        初始化账号的首次延期时间
        
        实现说明:
        1. 对于新账号，设置首次延期时间
        2. 首次延期时间为 first_delay_days 天后
        """
        accounts = config.get_enabled_accounts()
        
        for account in accounts:
            account_state_manager.set_initial_next_delay_time(
                platform=account.platform,
                username=account.username,
                first_delay_days=account.first_delay_days,
            )
    
    def _setup_verification_job(self):
        """
        配置验证任务
        
        实现说明:
        1. 每10分钟检查一次待验证的账号
        2. 对已到验证时间的账号进行验证
        3. 验证失败时发送通知
        """
        trigger = IntervalTrigger(minutes=10)
        
        self.scheduler.add_job(
            self._run_verification_task,
            trigger=trigger,
            id='verification_task',
            name='延期验证任务',
            replace_existing=True,
        )
        
        logger.info('验证任务已配置: 每10分钟检查一次')
    
    def _check_missed_tasks(self):
        """
        检查错过的延期任务（启动时调用）
        
        实现说明:
        1. 检查是否有 next_delay_time 已过期的账号
        2. 记录日志并立即执行
        """
        missed = account_state_manager.get_missed_accounts()
        
        if not missed:
            return
        
        logger.info('='*50)
        logger.info(f'发现 {len(missed)} 个账号有错过的延期任务')
        logger.info('='*50)
        
        for acc in missed:
            logger.warning(
                f'账号 [{acc["platform"]}] {acc["username"]} '
                f'延期任务已过期 {acc["overdue_hours"]:.1f} 小时，'
                f'连续失败 {acc["consecutive_failures"]} 次'
            )
        
        logger.info('将立即执行这些错过的延期任务')
    
    def _check_and_run_delay_tasks(self):
        """
        检查并执行延期任务
        
        实现说明:
        1. 获取所有启用的账号
        2. 检查每个账号是否应该执行延期
        3. 对需要延期的账号执行延期操作
        4. 使用锁确保并发安全
        """
        logger.info('检查是否需要执行延期任务...')
        
        accounts = config.get_enabled_accounts()
        
        if not accounts:
            return
        
        accounts_to_delay = []
        
        for account in accounts:
            if account_state_manager.is_max_retries_exceeded(account.platform, account.username):
                continue
            
            if account_state_manager.should_delay(account.platform, account.username):
                accounts_to_delay.append(account)
        
        if not accounts_to_delay:
            logger.info('没有账号需要延期')
            return
        
        logger.info(f'发现 {len(accounts_to_delay)} 个账号需要延期')
        
        for account in accounts_to_delay:
            with self._account_lock:
                account_key = f"{account.platform}:{account.username}"
                if account_key in self._running_accounts:
                    logger.warning(f'账号 {account.username} 正在执行中，跳过')
                    continue
                self._running_accounts.add(account_key)
            
            try:
                self._process_single_account_safe(account)
            finally:
                with self._account_lock:
                    account_key = f"{account.platform}:{account.username}"
                    self._running_accounts.discard(account_key)
            
            time.sleep(3)
    
    def _process_single_account_safe(self, account: AccountConfig):
        """
        安全地处理单个账号的延期（带锁）
        
        Args:
            account: 账号配置
        """
        logger.info(f'开始处理账号: [{account.platform}] {account.username}')
        
        consecutive_failures_before = account_state_manager.get_consecutive_failures(
            account.platform, account.username
        )
        
        try:
            success, message = self._process_single_account(account)
            
            account_state_manager.record_delay(
                platform=account.platform,
                username=account.username,
                success=success,
                message=message,
                delay_interval_days=account.delay_interval_days,
            )
            
            if success:
                logger.info(f'账号 {account.username} 延期申请成功')
            else:
                logger.error(f'账号 {account.username} 延期申请失败: {message}')
                
                consecutive_failures_after = account_state_manager.get_consecutive_failures(
                    account.platform, account.username
                )
                
                if consecutive_failures_after >= self.FAILURE_WARNING_THRESHOLD:
                    self._send_consecutive_failure_warning(account, consecutive_failures_after, message)
                
                if account_state_manager.is_max_retries_exceeded(account.platform, account.username):
                    self._send_max_retries_exceeded_notification(account, consecutive_failures_after)
            
        except Exception as e:
            logger.error(f'处理账号 {account.username} 时发生异常: {e}')
            
            account_state_manager.record_delay(
                platform=account.platform,
                username=account.username,
                success=False,
                message=f'异常: {str(e)}',
                delay_interval_days=account.delay_interval_days,
            )
            
            consecutive_failures_after = account_state_manager.get_consecutive_failures(
                account.platform, account.username
            )
            
            if consecutive_failures_after >= self.FAILURE_WARNING_THRESHOLD:
                self._send_consecutive_failure_warning(account, consecutive_failures_after, str(e))
    
    def _process_single_account(self, account: AccountConfig) -> Tuple[bool, str]:
        """
        处理单个账号的延期
        
        Returns:
            (success: bool, message: str)
        """
        with create_client(account.platform, account.username, account.password) as client:
            success, message = client.login()
            if not success:
                logger.error(f'账号 {account.username} 登录失败: {message}')
                state_manager.record_submission(
                    platform=account.platform,
                    username=account.username,
                    ptype=account.ptype,
                    post_url=account.post_url,
                    screenshot_path=account.screenshot_path,
                    success=False,
                    message=f'登录失败: {message}',
                    verification_delay_hours=config.verification_delay_hours,
                )
                return False, f'登录失败: {message}'
            
            logger.info(f'账号 {account.username} 登录成功')
            
            success, message = client.submit_delay(
                post_url=account.post_url,
                screenshot_path=account.screenshot_path,
                ptype=account.ptype,
            )
            
            state_manager.record_submission(
                platform=account.platform,
                username=account.username,
                ptype=account.ptype,
                post_url=account.post_url,
                screenshot_path=account.screenshot_path,
                success=success,
                message=message,
                verification_delay_hours=config.verification_delay_hours,
            )
            
            return success, message
    
    def _send_delay_failed_notification(self, account: AccountConfig, message: str):
        """发送延期失败通知"""
        notifier = create_notifier_from_config()
        
        results = [{
            'username': account.username,
            'platform': account.platform,
            'success': False,
            'message': message,
        }]
        
        summary = {
            'total': 1,
            'success': 0,
            'fail': 1,
        }
        
        notifier.send_notification('延期任务执行失败', results, summary)
    
    def _send_consecutive_failure_warning(self, account: AccountConfig, failures: int, message: str):
        """
        发送连续失败警告
        
        实现说明:
        当连续失败达到阈值时发送警告，提醒用户关注
        """
        logger.warning(f'账号 [{account.platform}] {account.username} 已连续失败 {failures} 次')
        
        notifier = create_notifier_from_config()
        
        title = f'延期连续失败警告 ({failures}次)'
        
        results = [{
            'username': account.username,
            'platform': account.platform,
            'success': False,
            'message': f'连续失败 {failures} 次: {message}',
        }]
        
        summary = {
            'total': 1,
            'success': 0,
            'fail': 1,
        }
        
        notifier.send_notification(title, results, summary)
    
    def _send_max_retries_exceeded_notification(self, account: AccountConfig, failures: int):
        """
        发送最大重试次数超限通知
        
        实现说明:
        当连续失败达到最大重试次数时发送紧急通知
        """
        logger.error(f'账号 [{account.platform}] {account.username} 已达到最大重试次数 {failures} 次，停止自动重试')
        
        notifier = create_notifier_from_config()
        
        title = f'【紧急】延期自动重试已停止'
        
        results = [{
            'username': account.username,
            'platform': account.platform,
            'success': False,
            'message': f'连续失败 {failures} 次，已达到最大重试次数，自动重试已停止。请手动检查并处理。',
        }]
        
        summary = {
            'total': 1,
            'success': 0,
            'fail': 1,
        }
        
        notifier.send_verification_failed_notification(title, results, summary)
    
    def _run_verification_task(self):
        """
        执行验证任务
        
        实现说明:
        1. 获取待验证的账号列表
        2. 对每个账号尝试再次提交延期
        3. 如果提交成功，说明上次延期失败
        4. 如果提交失败（已提交过），说明上次延期成功
        5. 验证失败时发送邮件通知
        """
        pending = state_manager.get_pending_verifications()
        
        if not pending:
            return
        
        logger.info('='*50)
        logger.info(f'开始执行延期验证任务，共 {len(pending)} 个账号待验证')
        logger.info('='*50)
        
        failed_accounts = []
        
        for state in pending:
            platform = state['platform']
            username = state['username']
            ptype = state['ptype']
            post_url = state['post_url']
            screenshot_path = state['screenshot_path']
            
            logger.info(f'验证账号: [{platform}] {username}')
            
            try:
                verify_success, verify_message = self._verify_delay(
                    platform=platform,
                    username=username,
                    password=self._get_password_for_account(platform, username),
                    post_url=post_url,
                    screenshot_path=screenshot_path,
                    ptype=ptype,
                )
                
                state_manager.record_verification(
                    platform=platform,
                    username=username,
                    verify_success=verify_success,
                    verify_message=verify_message,
                )
                
                if verify_success:
                    failed_accounts.append({
                        'platform': platform,
                        'username': username,
                        'message': '上次延期未生效，本次重新提交成功',
                    })
                
            except Exception as e:
                logger.error(f'验证账号 {username} 时发生异常: {e}')
                state_manager.record_verification(
                    platform=platform,
                    username=username,
                    verify_success=False,
                    verify_message=f'验证异常: {str(e)}',
                )
            
            time.sleep(2)
        
        if failed_accounts:
            self._send_verification_failed_notification(failed_accounts)
        
        logger.info('='*50)
        logger.info('延期验证任务执行完成')
        logger.info('='*50)
    
    def _get_password_for_account(self, platform: str, username: str) -> str:
        """获取账号密码"""
        for account in config.accounts:
            if account.platform == platform and account.username == username:
                return account.password
        return ''
    
    def _verify_delay(
        self,
        platform: str,
        username: str,
        password: str,
        post_url: str,
        screenshot_path: str,
        ptype: str,
    ) -> Tuple[bool, str]:
        """
        验证延期是否成功
        
        实现说明:
        1. 登录账号
        2. 尝试提交延期
        3. 如果提交成功，说明上次延期失败（本次是新的延期）
        4. 如果提交失败（提示已提交），说明上次延期成功
        
        Returns:
            (verify_success: bool, message: str)
            verify_success=True 表示验证发现上次延期失败
            verify_success=False 表示验证确认上次延期成功
        """
        with create_client(platform, username, password) as client:
            success, message = client.login()
            if not success:
                logger.error(f'验证登录失败: {message}')
                return False, f'登录失败: {message}'
            
            success, message = client.submit_delay(
                post_url=post_url,
                screenshot_path=screenshot_path,
                ptype=ptype,
            )
            
            if success:
                logger.warning(f'验证发现上次延期失败，本次重新提交成功')
                return True, '上次延期未生效，已重新提交'
            else:
                success_keywords = ['已提交', '已经', '重复', '还没有到可以提交延期的时间', '待审核', '审核中']
                if any(keyword in message for keyword in success_keywords):
                    logger.info(f'验证确认上次延期已生效: {message}')
                    return False, f'上次延期已生效: {message}'
                else:
                    logger.warning(f'验证提交失败: {message}')
                    return False, f'验证提交失败: {message}'
    
    def _send_verification_failed_notification(self, failed_accounts: List[Dict[str, Any]]):
        """
        发送验证失败通知
        
        Args:
            failed_accounts: 验证失败的账号列表
        """
        notifier = create_notifier_from_config()
        
        title = '延期验证失败通知'
        
        results = []
        for acc in failed_accounts:
            results.append({
                'username': acc['username'],
                'platform': acc['platform'],
                'success': False,
                'message': acc['message'],
            })
        
        summary = {
            'total': len(failed_accounts),
            'success': 0,
            'fail': len(failed_accounts),
        }
        
        notifier.send_verification_failed_notification(title, results, summary)
    
    def start(self):
        """启动调度器"""
        self._check_missed_tasks()
        
        self.scheduler.start()
        logger.info('定时任务调度器已启动')
        
        self._check_and_run_delay_tasks()
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=True)
        logger.info('定时任务调度器已停止')
    
    def _process_single_account_with_timeout(self, account: AccountConfig, timeout_seconds: int = 120) -> Tuple[bool, str]:
        """
        处理单个账号，带超时保护
        
        Args:
            account: 账号配置
            timeout_seconds: 超时时间（秒）
            
        Returns:
            (success: bool, message: str)
        """
        result = {'success': False, 'message': '未知错误'}
        
        def target():
            nonlocal result
            try:
                success, message = self._process_single_account(account)
                result = {'success': success, 'message': message}
            except Exception as e:
                result = {'success': False, 'message': f'异常: {str(e)}'}
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            logger.error(f'账号 [{account.platform}] {account.username} 处理超时（{timeout_seconds}秒）')
            return False, f'处理超时（{timeout_seconds}秒）'
        
        return result['success'], result['message']

    def run_once(self):
        """立即执行一次（用于测试）"""
        logger.info('手动触发延期任务执行')
        
        accounts = config.get_enabled_accounts()
        
        if not accounts:
            logger.warning('没有启用的账号')
            return
        
        results = []
        for account in accounts:
            logger.info(f'处理账号: [{account.platform}] {account.username}')
            
            try:
                # 使用带超时保护的版本
                success, message = self._process_single_account_with_timeout(account, timeout_seconds=120)
                
                account_state_manager.record_delay(
                    platform=account.platform,
                    username=account.username,
                    success=success,
                    message=message,
                    delay_interval_days=account.delay_interval_days,
                )
                
                results.append({
                    'username': account.username,
                    'platform': account.platform,
                    'success': success,
                    'message': message,
                })
            except Exception as e:
                logger.error(f'处理账号 {account.username} 时发生异常: {e}')
                results.append({
                    'username': account.username,
                    'platform': account.platform,
                    'success': False,
                    'message': f'异常: {str(e)}',
                })
            
            time.sleep(2)
        
        self._print_summary(results)
    
    def run_verification_once(self):
        """立即执行一次验证任务（用于测试）"""
        logger.info('手动触发验证任务执行')
        self._run_verification_task()
    
    def get_next_run_time(self) -> datetime:
        """获取下次执行时间（最近的任务）"""
        jobs = self.scheduler.get_jobs()
        if jobs:
            next_times = []
            for job in jobs:
                try:
                    now = datetime.now().replace(tzinfo=None)
                    next_fire = job.trigger.get_next_fire_time(None, now)
                    if next_fire:
                        next_times.append(next_fire.replace(tzinfo=None))
                except (TypeError, AttributeError):
                    pass
            if next_times:
                return min(next_times)
        return None
    
    def get_all_next_run_times(self) -> Dict[str, datetime]:
        """获取所有任务的下次执行时间"""
        result = {}
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            try:
                now = datetime.now().replace(tzinfo=None)
                next_fire = job.trigger.get_next_fire_time(None, now)
                if next_fire:
                    result[job.name] = next_fire.replace(tzinfo=None)
            except (TypeError, AttributeError):
                pass
        return result
    
    def get_account_next_delay_times(self) -> Dict[str, datetime]:
        """获取所有账号的下次延期时间"""
        result = {}
        accounts = config.get_enabled_accounts()
        
        for account in accounts:
            next_time = account_state_manager.get_next_delay_time(
                platform=account.platform,
                username=account.username,
            )
            key = f"{account.platform}:{account.username}"
            result[key] = next_time
        
        return result
    
    def _print_summary(self, results: list):
        """打印执行摘要"""
        total = len(results)
        success_count = sum(1 for r in results if r['success'])
        fail_count = total - success_count
        
        logger.info('执行摘要:')
        logger.info(f'  总计: {total} 个账号')
        logger.info(f'  成功: {success_count} 个')
        logger.info(f'  失败: {fail_count} 个')
        
        if fail_count > 0:
            logger.info('失败详情:')
            for result in results:
                if not result['success']:
                    logger.info(f"  - [{result.get('platform', 'unknown')}] {result['username']}: {result['message']}")
