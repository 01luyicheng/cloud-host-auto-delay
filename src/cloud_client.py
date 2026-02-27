"""
云主机平台抽象基类模块

文件用途: 定义云主机平台的通用API客户端接口
创建日期: 2026-02-19
输入: 账号信息（用户名、密码、发帖地址、截图路径）
输出: 登录会话、延期操作结果
依赖: requests>=2.31.0

实现说明:
1. 定义云主机平台的通用接口（登录、获取延期列表、提交延期）
2. 实现通用的HTTP请求逻辑（重试、频率控制、错误处理）
3. 子类只需提供平台特定的配置（API域名、请求头等）

支持的API端点格式（三丰云和阿贝云通用）:
- 登录API: {API_BASE}/login.php
  - 方法: POST
  - 参数: cmd=login, id_mobile=手机号, password=密码
  
- 获取延期列表API: {API_BASE}/renew.php
  - 方法: POST
  - 参数: cmd=free_delay_list, page=1, count=4, ptype=vps/vhost
  
- 提交延期申请API: {API_BASE}/renew.php
  - 方法: POST (multipart/form-data)
  - 参数: cmd=free_delay_add, ptype=vps/vhost, url=发帖地址
  - 文件: yanqi_img=截图文件
"""

import time
import json
import re
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, ClassVar
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.logger import logger, log_account_operation


class CloudHostClient(ABC):
    """云主机平台HTTP客户端抽象基类"""
    
    API_BASE: ClassVar[str] = ''
    WEB_ORIGIN: ClassVar[str] = ''
    PLATFORM_NAME: ClassVar[str] = ''
    
    LOGIN_URL: ClassVar[str] = ''
    RENEW_URL: ClassVar[str] = ''
    
    def __init__(self, username: str, password: str):
        """
        初始化客户端

        实现说明:
        1. 创建requests.Session保持会话状态
        2. 配置重试策略（连接失败时重试3次）
        3. 设置通用请求头模拟浏览器行为
        4. 初始化请求频率控制
        """
        self.username = username
        self.password = password
        self.session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.WEB_ORIGIN,
            'Referer': f'{self.WEB_ORIGIN}/',
        })

        self.is_logged_in = False
        self.last_request_time = 0
        self.min_request_interval = 1.0

    def _log_request_response(self, method: str, url: str, params: Dict = None, 
                               data: Dict = None, response: requests.Response = None,
                               error: str = None):
        """
        记录请求和响应的详细信息到日志

        实现说明:
        1. 记录请求方法、URL、参数
        2. 记录响应状态码、响应内容
        3. 如果有错误，记录错误信息
        4. 敏感信息（密码）自动脱敏

        Args:
            method: HTTP方法
            url: 请求URL
            params: 查询参数
            data: 请求体数据
            response: 响应对象
            error: 错误信息
        """
        log_lines = [f'[{self.PLATFORM_NAME}] HTTP请求详情:']
        log_lines.append(f'  账号: {self.username}')
        log_lines.append(f'  方法: {method}')
        log_lines.append(f'  URL: {url}')

        def _mask_sensitive(payload: Dict[str, Any]) -> Dict[str, Any]:
            sensitive_keys = {'password', 'passwd', 'token', 'secret'}
            return {
                key: ('***' if str(key).lower() in sensitive_keys else value)
                for key, value in payload.items()
            }
        
        if params:
            safe_params = _mask_sensitive(params)
            log_lines.append(f'  查询参数: {json.dumps(safe_params, ensure_ascii=False)}')
        
        if data:
            safe_data = _mask_sensitive(data)
            log_lines.append(f'  请求数据: {json.dumps(safe_data, ensure_ascii=False)}')
        
        if response:
            log_lines.append(f'  响应状态码: {response.status_code}')
            log_lines.append(f'  响应头: {dict(response.headers)}')
            content = response.text[:2000] if len(response.text) > 2000 else response.text
            log_lines.append(f'  响应内容: {content}')
        
        if error:
            log_lines.append(f'  错误: {error}')
        
        logger.info('\n'.join(log_lines))

    def _wait_for_rate_limit(self):
        """
        请求频率控制

        实现说明:
        1. 计算距离上次请求的时间间隔
        2. 如果间隔小于最小间隔，则等待
        3. 更新最后请求时间
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            logger.debug(f'请求频率控制: 等待 {wait_time:.2f} 秒')
            time.sleep(wait_time)

        self.last_request_time = time.time()

    def _parse_json_response(self, response: requests.Response) -> Tuple[bool, Dict[str, Any], str]:
        """
        解析JSON响应（处理服务器返回的格式错误JSON）

        实现说明:
        1. 尝试直接解析JSON
        2. 失败时尝试修复常见的格式错误
        3. 处理BOM字符和编码问题

        Args:
            response: requests响应对象

        Returns:
            (success: bool, data: dict, raw_text: str)
        """
        content = response.content
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        
        text = content.decode('utf-8', errors='ignore').strip()
        
        if not text:
            return False, {}, '服务器返回空响应'
        
        try:
            result = json.loads(text)
            return True, result, text
        except ValueError as e:
            logger.warning(f'JSON格式错误，尝试修复: {text[:200]}')
            logger.debug(f'JSON解析错误: {e}')
            
            fixed_text = text.strip()
            if fixed_text.startswith('\ufeff'):
                fixed_text = fixed_text[1:]
            fixed_text = re.sub(r'""(\d+)"', r'"\1"', fixed_text)
            fixed_text = re.sub(r':"([^"]*)"([^":,}]+)"', r':"\1\2"', fixed_text)
            fixed_text = re.sub(r'"rresponse"', r'"response"', fixed_text)
            
            try:
                result = json.loads(fixed_text)
                logger.info('JSON格式修复成功')
                return True, result, text
            except ValueError as e2:
                logger.error(f'无法修复JSON格式: {e2}')
                return False, {}, text

    def login(self, max_retries: int = 3) -> Tuple[bool, str]:
        """
        登录云主机平台
        
        实现说明:
        1. 构造登录表单数据（cmd=login, id_mobile, password）
        2. 发送POST请求到登录API
        3. 解析JSON响应判断登录结果
        4. 失败时自动重试
        
        Returns:
            (success: bool, message: str)
        """
        for attempt in range(max_retries):
            try:
                logger.info(f'账号 {self.username} 尝试登录 {self.PLATFORM_NAME} (第{attempt + 1}次)')
                
                login_data = {
                    'cmd': 'login',
                    'id_mobile': self.username,
                    'password': self.password,
                }

                self._wait_for_rate_limit()

                response = self.session.post(
                    self.LOGIN_URL,
                    data=login_data,
                    timeout=30,
                )
                response.raise_for_status()
                
                self._log_request_response('POST', self.LOGIN_URL, data=login_data, response=response)
                
                success, result, raw_text = self._parse_json_response(response)
                if not success:
                    return False, '服务器返回无效响应'
                
                response_code = result.get('response') or result.get('rresponse')
                if response_code == '200':
                    self.is_logged_in = True
                    log_account_operation(self.username, '登录', '成功', platform=self.PLATFORM_NAME)
                    logger.info(f'登录成功，跳转URL: {result.get("url", "unknown")}')
                    return True, '登录成功'
                elif response_code == '500104':
                    msg = result.get('msg', '账号已被锁定')
                    logger.error(f'账号被锁定: {msg}')
                    return False, f'账号被锁定: {msg}'
                else:
                    msg = result.get('msg', '未知错误')
                    logger.error(f'登录失败: {msg}')
                    return False, f'登录失败: {msg}'
                
            except requests.exceptions.RequestException as e:
                self._log_request_response('POST', self.LOGIN_URL, data=login_data, error=str(e))
                logger.error(f'登录请求异常: {e}')
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f'{wait_time}秒后重试...')
                    time.sleep(wait_time)
                else:
                    return False, f'登录请求失败: {str(e)}'
            except Exception as e:
                logger.error(f'登录过程异常: {e}')
                return False, f'登录异常: {str(e)}'
        
        return False, '登录失败，已达到最大重试次数'
    
    def get_delay_list(self, ptype: str = 'vps') -> Tuple[bool, list, str]:
        """
        获取延期列表
        
        实现说明:
        1. 使用renew.php端点的free_delay_list命令
        2. 添加page、count、ptype参数
        3. 返回延期记录列表（历史延期记录）
        
        Args:
            ptype: 产品类型，'vps'（云服务器）或 'vhost'（虚拟主机）
            
        Returns:
            (success: bool, data: list, message: str)
        """
        if not self.is_logged_in:
            return False, [], '未登录，请先调用login()'
        
        try:
            params = {
                'cmd': 'free_delay_list',
                'page': '1',
                'count': '20',
                'ptype': ptype,
            }
            
            logger.info(f'获取延期列表: {self.RENEW_URL} 参数: {params}')

            self._wait_for_rate_limit()

            response = self.session.post(self.RENEW_URL, data=params, timeout=30)
            logger.info(f'响应状态码: {response.status_code}')
            
            success, result, raw_text = self._parse_json_response(response)
            if not success:
                return False, [], raw_text
            
            response_code = result.get('response') or result.get('rresponse')
            if response_code == '200':
                msg = result.get('msg', {})
                if isinstance(msg, dict):
                    data = msg.get('content', [])
                else:
                    data = []
                logger.info(f'获取延期列表成功，共 {len(data)} 条记录')
                return True, data, '获取成功'
            else:
                msg = result.get('msg', '未知错误')
                return False, [], f'获取失败: {msg}'
                
        except requests.exceptions.RequestException as e:
            logger.error(f'获取延期列表失败: {e}')
            return False, [], f'请求失败: {str(e)}'
    
    def submit_delay(self, post_url: str, screenshot_path: str, ptype: str = 'vps', max_retries: int = 3) -> Tuple[bool, str]:
        """
        提交延期申请
        
        实现说明:
        1. 使用renew.php端点的free_delay_add命令
        2. 文件字段名使用yanqi_img
        3. 需要指定ptype参数（vps或vhost）
        4. 不需要指定服务器ID，系统会自动处理
        
        Args:
            post_url: 发帖地址
            screenshot_path: 截图文件路径
            ptype: 产品类型，'vps'（云服务器）或 'vhost'（虚拟主机）
            max_retries: 最大重试次数
            
        Returns:
            (success: bool, message: str)
        """
        if not self.is_logged_in:
            return False, '未登录，请先调用login()'
        
        screenshot_file = Path(screenshot_path)
        if not screenshot_file.exists():
            return False, f'截图文件不存在: {screenshot_path}'
        
        logger.info(f'提交延期申请: ptype={ptype}, url={post_url}, screenshot={screenshot_path}')
        
        for attempt in range(max_retries):
            try:
                delay_data = {
                    'cmd': 'free_delay_add',
                    'ptype': ptype,
                    'url': post_url,
                    'screenshot': screenshot_path,
                }

                self._wait_for_rate_limit()

                with open(screenshot_file, 'rb') as f:
                    files = {
                        'yanqi_img': (screenshot_file.name, f, 'image/jpeg'),
                    }

                    response = self.session.post(
                        self.RENEW_URL,
                        data={'cmd': 'free_delay_add', 'ptype': ptype, 'url': post_url},
                        files=files,
                        timeout=60,
                    )
                
                response.raise_for_status()
                
                self._log_request_response('POST', self.RENEW_URL, data=delay_data, response=response)
                
                success, result, raw_text = self._parse_json_response(response)
                if not success:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return False, '响应格式错误'
                
                response_code = result.get('response') or result.get('rresponse')
                if response_code == '200':
                    msg = result.get('msg', '提交成功')
                    logger.info(f'延期申请成功: {msg}')
                    log_account_operation(self.username, '延期申请', '成功', f'ptype={ptype}', platform=self.PLATFORM_NAME)
                    return True, f'延期申请成功: {msg}'
                else:
                    msg = result.get('msg', '未知错误')
                    logger.warning(f'延期申请失败: {msg}')
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    log_account_operation(self.username, '延期申请', '失败', msg, platform=self.PLATFORM_NAME)
                    return False, f'延期申请失败: {msg}'
                    
            except requests.exceptions.RequestException as e:
                self._log_request_response('POST', self.RENEW_URL, data=delay_data, error=str(e))
                logger.error(f'延期请求异常: {e}')
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f'{wait_time}秒后重试...')
                    time.sleep(wait_time)
                else:
                    log_account_operation(self.username, '延期申请', '异常', str(e), platform=self.PLATFORM_NAME)
                    return False, f'请求失败: {str(e)}'
            except Exception as e:
                logger.error(f'延期过程异常: {e}')
                log_account_operation(self.username, '延期申请', '异常', str(e), platform=self.PLATFORM_NAME)
                return False, f'异常: {str(e)}'
        
        return False, '延期申请失败，已达到最大重试次数'
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class AbeiyunClient(CloudHostClient):
    """阿贝云HTTP客户端"""
    
    API_BASE = 'https://api.abeiyun.com/www'
    WEB_ORIGIN = 'https://www.abeiyun.com'
    PLATFORM_NAME = '阿贝云'
    
    LOGIN_URL = f'{API_BASE}/login.php'
    RENEW_URL = f'{API_BASE}/renew.php'


class SanfengyunClient(CloudHostClient):
    """三丰云HTTP客户端"""
    
    API_BASE = 'https://api.sanfengyun.com/www'
    WEB_ORIGIN = 'https://www.sanfengyun.com'
    PLATFORM_NAME = '三丰云'
    
    LOGIN_URL = f'{API_BASE}/login.php'
    RENEW_URL = f'{API_BASE}/renew.php'


def create_client(platform: str, username: str, password: str) -> CloudHostClient:
    """
    创建云主机客户端工厂函数
    
    Args:
        platform: 平台名称，支持 'abeiyun'（阿贝云）或 'sanfengyun'（三丰云）
        username: 用户名（手机号）
        password: 密码
        
    Returns:
        CloudHostClient实例
        
    Raises:
        ValueError: 不支持的平台名称
    """
    platform = platform.lower()
    
    if platform == 'abeiyun':
        return AbeiyunClient(username, password)
    elif platform == 'sanfengyun':
        return SanfengyunClient(username, password)
    else:
        raise ValueError(f'不支持的平台: {platform}，支持的平台: abeiyun, sanfengyun')
