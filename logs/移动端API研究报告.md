# 阿贝云移动端站点API研究报告

**研究时间**: 2026-02-18
**测试账号**: 13605720328 / Luyicheng@0505
**移动端站点**: https://m.abeiyun.com
**桌面端站点**: https://www.abeiyun.com

---

## 执行摘要

### 关键发现

1. **移动端没有独立API端点**: `https://m.abeiyun.com/api/*` 返回404错误
2. **移动端与桌面端共享API**: 移动端站点直接使用桌面端API端点
3. **Vue.js单页应用**: 移动端使用Vue.js框架，通过`https://api.abeiyun.com/www/*`访问API

### 结论

移动端站点 **m.abeiyun.com** 没有独立的API端点，而是使用与桌面端相同的API：
- **API基础URL**: `https://api.abeiyun.com/www`
- **登录API**: `login.php`
- **VPS管理API**: `vps.php`
- **延期申请API**: `vps.php` (cmd=free_delay)
- **续费/延期查询API**: `renew.php`

---

## 详细分析

### 1. 移动端站点架构

#### 技术栈
- **前端框架**: Vue.js 2.x
- **UI组件库**: Vux (基于WeUI的Vue组件库)
- **HTTP客户端**: Vue Resource (`this.$http`)
- **构建工具**: Webpack

#### 页面结构
移动端是一个单页应用（SPA），主要路由包括：
- `/` - 首页
- `/user/freevpsdelay` - 免费VPS延期页面
- `/login` - 登录页面
- `/control` - 控制面板

### 2. API端点发现

#### 从Vue.js代码中提取的API端点

| API端点 | 用途 | 发现位置 |
|---------|------|----------|
| `https://api.abeiyun.com/www/login.php` | 登录/登出 | app.js |
| `https://api.abeiyun.com/www/vps.php` | VPS管理（延期申请） | app.js |
| `https://api.abeiyun.com/www/vhost.php` | 虚拟主机管理 | app.js |
| `https://api.abeiyun.com/www/renew.php` | 续费/延期查询 | app.js |
| `https://api.abeiyun.com/www/user.php` | 用户信息 | app.js |
| `https://api.abeiyun.com/www/caiwu.php` | 财务管理 | app.js |
| `https://api.abeiyun.com/www/domain.php` | 域名管理 | app.js |
| `https://api.abeiyun.com/www/gd.php` | 工单系统 | app.js |
| `https://api.abeiyun.com/www/upgrade.php` | 升级服务 | app.js |
| `https://api.abeiyun.com/www/reg.php` | 注册 | app.js |
| `https://api.abeiyun.com/www/reset_pwd.php` | 密码重置 | app.js |
| `https://api.abeiyun.com/www/mianbeian.php` | 免备案服务 | app.js |
| `https://api.abeiyun.com/www/haomiao.php` | 推广活动 | app.js |
| `https://api.abeiyun.com/www/yzm.php` | 验证码 | app.js |
| `https://api.abeiyun.com/weixin/pay/jsapi.php` | 微信支付 | app.js |

### 3. 移动端与桌面端API对比

#### API端点对比

| 功能 | 移动端 | 桌面端 | 是否相同 |
|------|--------|--------|----------|
| 登录 | `https://api.abeiyun.com/www/login.php` | `https://api.abeiyun.com/www/login.php` | ✅ 相同 |
| VPS列表 | `https://api.abeiyun.com/www/vps.php` | `https://api.abeiyun.com/www/vps.php` | ✅ 相同 |
| 延期申请 | `https://api.abeiyun.com/www/vps.php` | `https://api.abeiyun.com/www/vps.php` | ✅ 相同 |
| 虚拟主机 | `https://api.abeiyun.com/www/vhost.php` | `https://api.abeiyun.com/www/vhost.php` | ✅ 相同 |
| 用户信息 | `https://api.abeiyun.com/www/user.php` | `https://api.abeiyun.com/www/user.php` | ✅ 相同 |

#### 请求头差异

**移动端请求头**:
```http
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
Origin: https://m.abeiyun.com
Referer: https://m.abeiyun.com/
```

**桌面端请求头**:
```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
Origin: https://www.abeiyun.com
Referer: https://www.abeiyun.com/
```

### 4. 延期相关API详解

#### 4.1 获取延期列表

**API端点**: `https://api.abeiyun.com/www/vps.php`

**请求方法**: POST

**请求参数**:
```json
{
  "cmd": "vps_list",
  "page": "1"
}
```

**响应示例**:
```json
{
  "msg": {
    "content": [],
    "allcount": 0,
    "pagecount": 20,
    "allpage": 0,
    "curpage": "1"
  },
  "response": "200"
}
```

#### 4.2 提交延期申请

**API端点**: `https://api.abeiyun.com/www/vps.php`

**请求方法**: POST

**Content-Type**: `multipart/form-data`

**请求参数**:
- `cmd`: `free_delay`
- `id`: 服务器ID
- `url`: 发帖地址
- `img`: 截图文件（文件上传）

**请求示例**:
```python
import requests

session = requests.Session()

# 登录
session.post(
    'https://api.abeiyun.com/www/login.php',
    data={'cmd': 'login', 'id_mobile': '手机号', 'password': '密码'}
)

# 提交延期申请
with open('screenshot.jpg', 'rb') as f:
    files = {'img': ('screenshot.jpg', f, 'image/jpeg')}
    response = session.post(
        'https://api.abeiyun.com/www/vps.php',
        data={
            'cmd': 'free_delay',
            'id': '服务器ID',
            'url': 'https://example.com/post',
        },
        files=files
    )
```

#### 4.3 续费/延期查询API

**API端点**: `https://api.abeiyun.com/www/renew.php`

**请求方法**: POST

**用途**: 查询续费和延期相关信息

### 5. 截图上传方式

#### 移动端截图上传

**上传方式**: multipart/form-data

**表单字段**:
- `cmd`: `free_delay`
- `id`: 服务器ID
- `url`: 发帖地址
- `img`: 截图文件

**文件要求**:
- **字段名**: `img`
- **Content-Type**: `image/jpeg` 或 `image/png`
- **文件名**: 原始文件名

**上传示例**:
```python
files = {
    'img': ('screenshot.jpg', open('screenshot.jpg', 'rb'), 'image/jpeg')
}
```

#### 与桌面端对比

移动端和桌面端的截图上传方式**完全相同**，都使用：
- 相同的API端点: `https://api.abeiyun.com/www/vps.php`
- 相同的请求方法: POST
- 相同的表单字段: `cmd`, `id`, `url`, `img`
- 相同的文件上传方式: multipart/form-data

### 6. 完整的API调用示例

#### Python代码示例

```python
import requests
import json

class AbeiyunMobileAPI:
    """阿贝云移动端API客户端"""
    
    API_BASE = 'https://api.abeiyun.com/www'
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        # 设置移动端请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://m.abeiyun.com',
            'Referer': 'https://m.abeiyun.com/',
        })
    
    def parse_response(self, response):
        """解析API响应（处理UTF-8 BOM）"""
        content = response.content
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        return json.loads(content.decode('utf-8', errors='ignore'))
    
    def login(self):
        """登录"""
        response = self.session.post(
            f'{self.API_BASE}/login.php',
            data={
                'cmd': 'login',
                'id_mobile': self.username,
                'password': self.password,
            }
        )
        result = self.parse_response(response)
        return result.get('response') == '200'
    
    def get_vps_list(self):
        """获取VPS列表"""
        response = self.session.post(
            f'{self.API_BASE}/vps.php',
            data={'cmd': 'vps_list', 'page': '1'}
        )
        result = self.parse_response(response)
        if result.get('response') == '200':
            return result.get('msg', {}).get('content', [])
        return []
    
    def submit_delay(self, vps_id: str, post_url: str, screenshot_path: str):
        """提交延期申请"""
        with open(screenshot_path, 'rb') as f:
            files = {'img': (screenshot_path.split('/')[-1], f, 'image/jpeg')}
            response = self.session.post(
                f'{self.API_BASE}/vps.php',
                data={
                    'cmd': 'free_delay',
                    'id': vps_id,
                    'url': post_url,
                },
                files=files
            )
        result = self.parse_response(response)
        return result.get('response') == '200'


# 使用示例
if __name__ == '__main__':
    api = AbeiyunMobileAPI('13605720328', 'Luyicheng@0505')
    
    # 登录
    if api.login():
        print('登录成功')
        
        # 获取VPS列表
        vps_list = api.get_vps_list()
        print(f'VPS列表: {vps_list}')
        
        # 提交延期申请（如果有VPS）
        if vps_list:
            for vps in vps_list:
                success = api.submit_delay(
                    vps_id=vps['id'],
                    post_url='https://example.com/post',
                    screenshot_path='screenshot.jpg'
                )
                print(f"延期申请{'成功' if success else '失败'}")
    else:
        print('登录失败')
```

#### cURL命令示例

**登录**:
```bash
curl -X POST 'https://api.abeiyun.com/www/login.php' \
  -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Origin: https://m.abeiyun.com' \
  -H 'Referer: https://m.abeiyun.com/' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d 'cmd=login&id_mobile=13605720328&password=Luyicheng@0505' \
  -c cookies.txt
```

**获取VPS列表**:
```bash
curl -X POST 'https://api.abeiyun.com/www/vps.php' \
  -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Origin: https://m.abeiyun.com' \
  -H 'Referer: https://m.abeiyun.com/' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d 'cmd=vps_list&page=1' \
  -b cookies.txt
```

**提交延期申请**:
```bash
curl -X POST 'https://api.abeiyun.com/www/vps.php' \
  -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Origin: https://m.abeiyun.com' \
  -H 'Referer: https://m.abeiyun.com/' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -F 'cmd=free_delay' \
  -F 'id=服务器ID' \
  -F 'url=https://example.com/post' \
  -F 'img=@screenshot.jpg' \
  -b cookies.txt
```

### 7. 测试结果

#### 登录API测试

**移动端请求**:
- URL: `https://m.abeiyun.com/api/login.php`
- 结果: ❌ 404 Not Found

**桌面端API（移动端使用）**:
- URL: `https://api.abeiyun.com/www/login.php`
- 结果: ✅ 200 OK
- 响应: `{"response": "200", "url": "/control", "msg": "登录成功"}`

#### VPS列表API测试

**移动端请求**:
- URL: `https://m.abeiyun.com/api/vps.php`
- 结果: ❌ 404 Not Found

**桌面端API（移动端使用）**:
- URL: `https://api.abeiyun.com/www/vps.php`
- 结果: ✅ 200 OK
- 响应: `{"msg": {"content": [], "allcount": 0, ...}, "response": "200"}`

#### 延期申请API测试

由于测试账号没有可延期的服务器，无法完整测试延期申请流程。但从Vue.js代码分析，延期申请使用与桌面端相同的API。

### 8. 重要发现

1. **移动端没有独立API**: 所有移动端API请求都指向桌面端API端点
2. **API完全兼容**: 移动端和桌面端使用完全相同的API
3. **请求头区分**: 通过User-Agent、Origin、Referer区分移动端和桌面端
4. **Vue.js架构**: 移动端使用Vue.js单页应用，通过Ajax调用API
5. **截图上传相同**: 移动端和桌面端的截图上传方式完全一致

### 9. 建议

1. **直接使用桌面端API**: 移动端自动化可以直接使用桌面端API端点
2. **设置正确的请求头**: 使用移动端User-Agent和Origin
3. **处理UTF-8 BOM**: API响应包含BOM标记，需要特殊处理
4. **保持会话**: 使用Session保持登录状态
5. **频率控制**: 避免频繁请求导致账号锁定

---

## 结论

### 移动端API总结

| 项目 | 详情 |
|------|------|
| **移动端站点** | https://m.abeiyun.com |
| **API基础URL** | https://api.abeiyun.com/www |
| **登录API** | POST /login.php (cmd=login) |
| **VPS列表API** | POST /vps.php (cmd=vps_list) |
| **延期申请API** | POST /vps.php (cmd=free_delay) |
| **截图上传** | multipart/form-data, 字段名: img |

### 移动端与桌面端差异

| 差异项 | 移动端 | 桌面端 |
|--------|--------|--------|
| **站点URL** | m.abeiyun.com | www.abeiyun.com |
| **API端点** | 相同 | 相同 |
| **User-Agent** | iPhone/iPad | Windows/Mac |
| **Origin** | https://m.abeiyun.com | https://www.abeiyun.com |
| **Referer** | https://m.abeiyun.com/ | https://www.abeiyun.com/ |
| **页面架构** | Vue.js SPA | 传统多页应用 |

### 最终结论

**移动端站点 m.abeiyun.com 没有独立的API端点**，而是使用与桌面端完全相同的API。移动端和桌面端的唯一区别在于前端页面架构和请求头信息，后端API是完全统一的。

对于自动化延期任务，可以直接使用桌面端API，只需将请求头中的User-Agent、Origin和Referer设置为移动端值即可。

---

**报告生成时间**: 2026-02-18
**报告版本**: v1.0
