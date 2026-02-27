"""
日志管理模块

文件用途: 配置和管理程序日志
创建日期: 2026-02-17
输入: 日志级别、日志消息
输出: 格式化的日志记录
依赖: python-json-logger>=2.0.7

实现说明:
1. 使用Python标准logging模块
2. 支持控制台和文件双输出
3. 日志文件按日期轮转
4. 包含详细的时间戳和上下文信息
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = 'abeiyun', log_dir: Path = None, log_level: str = 'INFO') -> logging.Logger:
    """
    配置并返回日志记录器
    
    实现说明:
    1. 创建logger实例
    2. 添加控制台处理器（输出到stdout）
    3. 添加文件处理器（按大小轮转，最大10MB，保留5个备份）
    4. 设置统一的日志格式
    
    Args:
        name: logger名称
        log_dir: 日志目录路径，如果为None则使用当前目录下的logs文件夹
        log_level: 日志级别
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志目录
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（按大小轮转）
    log_file = log_dir / f'{name}.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 错误日志单独文件
    error_file = log_dir / f'{name}_error.log'
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


# 全局日志实例
logger = setup_logger()


def log_account_operation(account: str, operation: str, status: str, message: str = '', platform: str = ''):
    """记录账号操作日志"""
    log_msg = f'[账号: {account}] [操作: {operation}] [状态: {status}]'
    if platform:
        log_msg = f'[{platform}] ' + log_msg
    if message:
        log_msg += f' - {message}'
    
    if status == '成功':
        logger.info(log_msg)
    elif status == '失败':
        logger.error(log_msg)
    else:
        logger.warning(log_msg)
