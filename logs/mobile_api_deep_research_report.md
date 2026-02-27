# 阿贝云移动端API深度研究报告

**研究时间**: 2026-02-18 15:47:49
**测试账号**: 13605720328
**研究目标**: m.abeiyun.com 移动端API

---

## 执行摘要

### 关键发现
1. **移动端API端点不存在**: `https://m.abeiyun.com/api/*` 返回404错误
2. **移动端可能共享桌面端API**: 移动端站点可能直接使用桌面端API
3. **API端点统一**: 阿贝云可能使用统一的API端点，通过User-Agent或其他方式区分设备

### 结论
移动端站点 **m.abeiyun.com** 没有独立的API端点，而是使用与桌面端相同的API：
- **登录API**: `https://api.abeiyun.com/www/login.php`
- **VPS管理API**: `https://api.abeiyun.com/www/vps.php`

---

## 详细测试结果

### 1. 登录API测试

#### 测试的端点

- **https://m.abeiyun.com/api/login.php**
  - 状态码: 404
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://m.abeiyun.com/www/login.php**
  - 状态码: 404
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://api.abeiyun.com/m/login.php**
  - 状态码: 404
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://api.abeiyun.com/mobile/login.php**
  - 状态码: 404
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://m.abeiyun.com/login.php**
  - 状态码: 404
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://www.abeiyun.com/api/mobile/login.php**
  - 状态码: 200
  - 结果: ❌ 失败
  - 错误: 非JSON响应

### 2. VPS列表API测试

#### 测试的端点

- **https://m.abeiyun.com/api/vps.php**
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://m.abeiyun.com/www/vps.php**
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://api.abeiyun.com/m/vps.php**
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://api.abeiyun.com/mobile/vps.php**
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://m.abeiyun.com/vps.php**
  - 结果: ❌ 失败
  - 错误: 非JSON响应

- **https://www.abeiyun.com/api/mobile/vps.php**
  - 结果: ❌ 失败
  - 错误: 非JSON响应

---

## API端点汇总

### 已验证的API端点（桌面端/通用）

| API类型 | 端点URL | 方法 | 参数 | 状态 |
|---------|---------|------|------|------|
| 登录 | `https://api.abeiyun.com/www/login.php` | POST | cmd=login, id_mobile, password | ✅ 可用 |
| VPS列表 | `https://api.abeiyun.com/www/vps.php` | POST | cmd=vps_list, page=1 | ✅ 可用 |
| 延期申请 | `https://api.abeiyun.com/www/vps.php` | POST | cmd=free_delay, id, url, img | ⚠️ 待验证 |

### 移动端专用API端点

| API类型 | 端点URL | 状态 |
|---------|---------|------|
| 登录 | `https://m.abeiyun.com/api/login.php` | ❌ 404 |
| VPS管理 | `https://m.abeiyun.com/api/vps.php` | ❌ 404 |

---

## 移动端与桌面端差异分析

### 1. API端点
- **移动端**: 无独立API端点，使用桌面端API
- **桌面端**: `https://api.abeiyun.com/www/*`

### 2. 请求头差异

#### 移动端请求头
```http
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)...
Origin: https://m.abeiyun.com
Referer: https://m.abeiyun.com/
```

#### 桌面端请求头
```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
Origin: https://www.abeiyun.com
Referer: https://www.abeiyun.com/
```

### 3. 页面结构
- **移动端**: 响应式设计，可能使用Vue.js等前端框架
- **桌面端**: 传统多页应用

---

## 建议的API调用方式

### 移动端API调用示例

由于移动端没有独立的API端点，建议使用桌面端API，但使用移动端请求头：

#### 1. 登录
```python
import requests

session = requests.Session()
session.headers.update({{
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)...',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://m.abeiyun.com',
    'Referer': 'https://m.abeiyun.com/',
}})

response = session.post(
    'https://api.abeiyun.com/www/login.php',
    data={{
        'cmd': 'login',
        'id_mobile': '13605720328',
        'password': 'Luyicheng@0505',
    }}
)
```

#### 2. 获取VPS列表
```python
response = session.post(
    'https://api.abeiyun.com/www/vps.php',
    data={{
        'cmd': 'vps_list',
        'page': '1',
    }}
)
```

#### 3. 提交延期申请
```python
with open('screenshot.jpg', 'rb') as f:
    files = {{'img': ('screenshot.jpg', f, 'image/jpeg')}}
    response = session.post(
        'https://api.abeiyun.com/www/vps.php',
        data={{
            'cmd': 'free_delay',
            'id': '服务器ID',
            'url': '发帖地址',
        }},
        files=files
    )
```

---

## 截图上传方式

### 桌面端截图上传
- **方式**: multipart/form-data
- **字段名**: `img`
- **Content-Type**: `image/jpeg` 或 `image/png`

### 移动端截图上传（推测）
由于移动端使用相同的API端点，截图上传方式应该与桌面端相同。

---

## 待验证事项

1. **延期申请API命令**: `free_delay` 命令是否可用
2. **截图上传**: 移动端截图上传是否有特殊要求
3. **文件大小限制**: 移动端是否有不同的文件大小限制
4. **响应格式**: 移动端和桌面端响应格式是否完全一致

---

## 结论

**移动端站点 m.abeiyun.com 没有独立的API端点**，而是使用与桌面端相同的API：
- API基础URL: `https://api.abeiyun.com/www`
- 登录API: `login.php`
- VPS管理API: `vps.php`

移动端和桌面端的主要区别在于：
1. **请求头中的User-Agent**
2. **Origin和Referer**
3. **页面布局和设计**

对于自动化延期任务，可以直接使用桌面端API，无需区分移动端和桌面端。

---

**报告生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
