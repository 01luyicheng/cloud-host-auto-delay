"""
阿贝云免费服务器自动延期程序主入口

文件用途: 程序主入口，处理命令行参数并启动调度器
创建日期: 2026-02-17
更新日期: 2026-02-18
输入: 命令行参数
输出: 程序执行结果
依赖: 见requirements.txt

实现说明:
1. 解析命令行参数
2. 根据参数执行不同操作（运行一次、启动调度、测试配置等）
3. 处理信号，确保优雅退出
4. 兼容Windows和Linux平台

使用方法:
    python main.py              # 启动定时任务调度器
    python main.py --once       # 立即执行一次延期任务
    python main.py --test       # 测试配置是否正确
    python main.py --account 13605720328  # 只处理指定账号
"""

import sys
import signal
import argparse
import time
import platform
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.logger import logger
from src.scheduler import DelayScheduler

IS_WINDOWS = platform.system() == 'Windows'


def signal_handler(signum, frame):
    """信号处理函数，用于优雅退出"""
    logger.info('收到终止信号，正在关闭...')
    sys.exit(0)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='阿贝云免费服务器自动延期程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py              # 启动定时任务调度器
  python main.py --once       # 立即执行一次延期任务
  python main.py --test       # 测试配置是否正确
  python main.py --account 13605720328  # 只处理指定账号
        '''
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='立即执行一次延期任务，然后退出'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='测试配置是否正确，验证账号配置和文件路径'
    )
    
    parser.add_argument(
        '--account',
        type=str,
        metavar='USERNAME',
        help='只处理指定用户名（手机号）的账号'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有配置的账号'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='显示调度器状态和下次执行时间'
    )
    
    return parser.parse_args()


def test_config():
    """测试配置"""
    logger.info('='*50)
    logger.info('测试配置')
    logger.info('='*50)
    
    accounts = config.accounts
    logger.info(f'共配置 {len(accounts)} 个账号')
    
    for idx, account in enumerate(accounts, 1):
        logger.info(f'\n账号 {idx}:')
        logger.info(f'  用户名: {account.username}')
        logger.info(f'  发帖地址: {account.post_url}')
        logger.info(f'  截图路径: {account.screenshot_path}')
        logger.info(f'  产品类型: {account.ptype}')
        logger.info(f'  执行时间: {account.schedule_hour:02d}:{account.schedule_minute:02d}')
        logger.info(f'  启用状态: {"启用" if account.enabled else "禁用"}')
        
        valid, msg = account.validate()
        if valid:
            logger.info(f'  验证结果: ✓ 通过')
        else:
            logger.error(f'  验证结果: ✗ 失败 - {msg}')
    
    logger.info(f'\n日志配置:')
    logger.info(f'  日志级别: {config.log_level}')
    logger.info(f'  日志目录: {config.log_dir}')
    
    logger.info('='*50)
    logger.info('配置测试完成')
    logger.info('='*50)


def list_accounts():
    """列出所有账号"""
    accounts = config.accounts
    
    if not accounts:
        print('未配置任何账号')
        return
    
    print(f'共 {len(accounts)} 个账号:')
    print('-' * 60)
    
    for idx, account in enumerate(accounts, 1):
        status = '启用' if account.enabled else '禁用'
        valid, msg = account.validate()
        valid_str = '✓' if valid else f'✗ ({msg})'
        
        print(f'{idx}. {account.username}')
        print(f'   状态: {status}')
        print(f'   验证: {valid_str}')
        print(f'   产品类型: {account.ptype}')
        print(f'   执行时间: {account.schedule_hour:02d}:{account.schedule_minute:02d}')
        print(f'   发帖地址: {account.post_url}')
        print(f'   截图路径: {account.screenshot_path}')
        print()


def run_single_account(username: str):
    """运行单个账号的延期任务"""
    from src.cloud_client import create_client
    
    account = None
    for acc in config.get_enabled_accounts():
        if acc.username == username:
            account = acc
            break
    
    if not account:
        logger.error(f'未找到账号: {username}')
        return
    
    logger.info(f'开始处理账号: {username}')
    
    with create_client(account.platform, account.username, account.password) as client:
        success, message = client.login()
        if not success:
            logger.error(f'登录失败: {message}')
            return
        
        logger.info('登录成功')
        
        success, message = client.submit_delay(
            post_url=account.post_url,
            screenshot_path=account.screenshot_path,
            ptype=account.ptype,
        )
        
        if success:
            logger.info(f'延期申请成功: {message}')
        else:
            logger.error(f'延期申请失败: {message}')


def show_status():
    """显示调度器状态"""
    import platform
    
    print('='*50)
    print('云主机自动延期程序状态')
    print('='*50)
    print(f'系统平台: {platform.system()} {platform.release()}')
    print(f'Python版本: {platform.python_version()}')
    print()
    
    accounts = config.get_enabled_accounts()
    print(f'配置账号数: {len(accounts)}')
    print()
    
    if accounts:
        print('账号列表:')
        for idx, account in enumerate(accounts, 1):
            print(f'  {idx}. {account.username} ({account.platform}/{account.ptype})')
            print(f'     首次延期: {account.first_delay_days}天后')
            print(f'     延期间隔: {account.delay_interval_days}天')
        print()
    
    scheduler = DelayScheduler()
    next_times = scheduler.get_all_next_run_times()
    
    if next_times:
        print('定时任务:')
        for name, next_time in sorted(next_times.items(), key=lambda x: x[1]):
            print(f'  {name}: {next_time}')
    else:
        print('定时任务: 无')
    
    print()
    
    account_next_times = scheduler.get_account_next_delay_times()
    if account_next_times:
        print('账号下次延期时间:')
        for key, next_time in sorted(account_next_times.items(), key=lambda x: x[1] if x[1] else datetime.max):
            if next_time:
                print(f'  {key}: {next_time}')
            else:
                print(f'  {key}: 待计算')
    
    print('='*50)


def main():
    """主函数"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
    args = parse_args()
    
    logger.info('阿贝云免费服务器自动延期程序启动')
    
    # 处理各种命令
    if args.test:
        test_config()
        return
    
    if args.list:
        list_accounts()
        return
    
    if args.status:
        show_status()
        return
    
    if args.account:
        run_single_account(args.account)
        return
    
    if args.once:
        # 立即执行一次
        scheduler = DelayScheduler()
        scheduler.run_once()
        return
    
    # 启动定时任务调度器
    scheduler = DelayScheduler()
    scheduler.start()
    
    # 显示下次执行时间
    next_run = scheduler.get_next_run_time()
    if next_run:
        logger.info(f'下次执行时间: {next_run}')
    
    logger.info('程序正在运行，按 Ctrl+C 停止')
    
    try:
        if IS_WINDOWS:
            while True:
                time.sleep(1)
        else:
            while True:
                signal.pause()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        logger.info('程序已停止')


if __name__ == '__main__':
    main()
