# 阿贝云API端点验证报告

**测试时间**: 2026-02-18 15:06:54
**测试账号**: 13605720328
**测试环境**: Windows 11, Python 3.14, requests 2.32.5

---

## 测试总结

### 整体评估
- **测试状态**: 部分成功
- **成功率**: 18.2% (2/11项测试通过)
- **主要问题**: 测试账号因频繁登录被暂时锁定，无法完成所有测试

### 关键发现
1. ✓ 登录API端点正确且可用
2. ✓ API响应格式符合预期（包含UTF-8 BOM标记）
3. ✓ 获取服务器列表API可用
4. ✗ 测试账号没有可延期的服务器
5. ✗ 测试账号被暂时锁定（需要等待10分钟）
6. ✗ 未检测到严格的反自动化机制

---

## 详细测试结果

### 1. 登录API端点验证

**API端点**: `https://api.abeiyun.com/www/login.php`

**测试结果**: ✓ 成功

**请求参数**:
```json
{
  "cmd": "login",
  "id_mobile": "13605720328",
  "password": "Luyicheng@0505"
}
```

**响应示例**:
```json
{
  "response": "200",
  "url": "/control",
  "msg": "登录成功"
}
```

**响应头**:
```
Content-Type: application/json
Server: Microsoft-IIS/8.5
X-Powered-By: PHP/7.0.8
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: https://www.abeiyun.com
Set-Cookie: session_id=1771398309636627197; path=/; domain=abeiyun.com
```

**重要发现**:
1. ✓ 登录成功时会设置`session_id` cookie
2. ✓ 响应包含UTF-8 BOM标记（`\xef\xbb\xbf`）
3. ✓ 响应格式为标准JSON
4. ✓ 成功响应码为"200"，失败时为其他数字

**错误密码测试**:
```json
{
  "response": "500103insert into config_pwd_error (userid) values('1882498')",
  "msg": "您的密码输入错误!6"
}
```

**账号锁定测试**:
```json
{
  "response": "500104",
  "msg": "当您看到这行字时，就不要再尝试了（请10分钟后重新输入）！"
}
```

**结论**: 登录API端点完全正确，需要正确处理UTF-8 BOM标记。

---

### 2. 获取延期列表API端点验证

**API端点**: `https://api.abeiyun.com/www/vps.php`

**测试结果**: ✓ 部分成功

#### 2.1 使用vps_list命令

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

**重要发现**:
1. ✓ 命令执行成功（response: "200"）
2. ✓ 该测试账号没有服务器（content为空数组）
3. ✓ 响应包含分页信息
4. ✓ 需要登录状态（session_id cookie）

#### 2.2 使用free_delay_list命令

**请求参数**:
```json
{
  "cmd": "free_delay_list",
  "ptype": "vps",
  "page": "1"
}
```

**响应**: 空响应（Content-Length: 3）

**重要发现**:
1. ✗ 该命令返回空响应
2. ✗ 可能该命令不存在或需要特定条件
3. ✗ 建议使用vps_list命令替代

**结论**:
- `vps_list`命令可用，可以获取服务器列表
- `free_delay_list`命令可能不存在或不可用
- 该测试账号没有可延期的服务器

---

### 3. 提交延期申请API端点验证

**API端点**: `https://api.abeiyun.com/www/vps.php`

**测试结果**: ✗ 无法完整测试（账号没有服务器）

**请求参数**:
```json
{
  "cmd": "free_delay",
  "id": "12345",
  "url": "https://example.com/post"
}
```

**响应**: 空响应（Content-Length: 3）

**重要发现**:
1. ✗ 该命令返回空响应
2. ✗ 可能该命令不存在或需要特定条件
3. ✗ 需要真实的服务器ID才能测试

**结论**: 无法完整测试，需要使用有服务器的账号进行测试。

---

### 4. 反自动化机制检查

#### 4.1 验证码机制
**测试结果**: ✗ 未检测到
- 登录页面没有验证码
- 可以直接提交登录请求

#### 4.2 Token机制
**测试结果**: ✗ 未检测到
- 登录成功后只设置了session_id cookie
- 没有发现其他token

#### 4.3 频率限制
**测试结果**: ⚠ 存在但宽松
- 快速发送5次登录请求，未触发429状态码
- 但连续失败后会锁定账号（10分钟）
- 建议控制请求频率，避免账号锁定

#### 4.4 User-Agent检测
**测试结果**: ✗ 未检测到
- 使用Python-requests User-Agent也能登录
- 没有严格的User-Agent验证

**结论**: 反自动化机制较弱，但存在账号锁定机制，需要控制请求频率。

---

## API端点正确性验证

### 已验证的API端点

| API端点 | 状态 | 说明 |
|---------|------|------|
| https://api.abeiyun.com/www/login.php | ✓ 正确 | 登录API，参数和响应格式正确 |
| https://api.abeiyun.com/www/vps.php | ✓ 正确 | VPS管理API，vps_list命令可用 |

### API命令列表

| 命令 | 状态 | 说明 |
|------|------|------|
| login | ✓ 可用 | 登录命令 |
| vps_list | ✓ 可用 | 获取服务器列表 |
| free_delay_list | ✗ 不可用 | 返回空响应 |
| free_delay | ✗ 不可用 | 返回空响应 |

### 响应格式

所有API响应都包含以下字段：
- `response`: 响应码，"200"表示成功
- `msg`: 消息内容，可能是字符串或对象
- 部分API还包含`url`、`data`等字段

**重要**: 所有响应都包含UTF-8 BOM标记，需要使用`utf-8-sig`编码或手动移除BOM。

---

## 代码实现建议

### 1. JSON解析处理

必须正确处理UTF-8 BOM标记：

```python
import json
import requests

def parse_json_with_bom(response: requests.Response) -> dict:
    """解析包含BOM的JSON响应"""
    content = response.content
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    text = content.decode('utf-8', errors='ignore')
    return json.loads(text)
```

### 2. 登录实现

```python
def login(username: str, password: str) -> Tuple[bool, str]:
    """登录阿贝云"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://www.abeiyun.com',
        'Referer': 'https://www.abeiyun.com/',
    })

    response = session.post(
        'https://api.abeiyun.com/www/login.php',
        data={
            'cmd': 'login',
            'id_mobile': username,
            'password': password,
        },
        timeout=30
    )

    result = parse_json_with_bom(response)
    if result.get('response') == '200':
        return True, '登录成功'
    else:
        return False, result.get('msg', '登录失败')
```

### 3. 获取服务器列表

```python
def get_vps_list(session: requests.Session) -> Tuple[bool, list, str]:
    """获取服务器列表"""
    response = session.post(
        'https://api.abeiyun.com/www/vps.php',
        data={
            'cmd': 'vps_list',
            'page': '1',
        },
        timeout=30
    )

    result = parse_json_with_bom(response)
    if result.get('response') == '200':
        msg = result.get('msg', {})
        content = msg.get('content', [])
        return True, content, '获取成功'
    else:
        return False, [], result.get('msg', '获取失败')
```

### 4. 错误处理

需要处理以下错误情况：
1. 账号锁定（response: "500104"）
2. 密码错误（response: "500103"）
3. 未登录（response: "50140"）
4. 网络错误
5. JSON解析错误

---

## 问题与建议

### 发现的问题

1. **free_delay_list命令不可用**
   - 该命令返回空响应
   - 建议使用vps_list命令获取服务器列表

2. **free_delay命令不可用**
   - 该命令返回空响应
   - 需要进一步调查延期申请的正确方式

3. **测试账号没有服务器**
   - 无法完整测试延期功能
   - 建议使用有服务器的账号进行测试

4. **账号锁定机制**
   - 连续失败后会锁定账号10分钟
   - 建议控制请求频率，避免账号锁定

### 建议

1. **使用vps_list命令**
   - 替代free_delay_list命令
   - 可以获取服务器列表

2. **调查延期申请方式**
   - 需要进一步调查延期申请的正确API命令
   - 可能需要通过网页端抓包分析

3. **使用有服务器的账号测试**
   - 需要使用有服务器的账号进行完整测试
   - 验证延期申请功能

4. **控制请求频率**
   - 避免短时间内多次登录
   - 建议每次登录间隔至少1分钟

5. **完善错误处理**
   - 处理账号锁定情况
   - 处理密码错误情况
   - 处理未登录情况

---

## 下一步行动

1. **等待账号解锁**
   - 等待10分钟后重新测试
   - 或者使用其他测试账号

2. **调查延期申请方式**
   - 通过网页端抓包分析延期申请的API
   - 确认正确的API命令和参数

3. **使用有服务器的账号测试**
   - 获取有服务器的测试账号
   - 完整测试延期申请功能

4. **完善代码实现**
   - 根据测试结果完善代码
   - 添加错误处理和重试机制

---

## 附录

### 测试环境
- 操作系统: Windows 11 25H2 x64
- Python版本: 3.14
- requests版本: 2.32.5
- 测试时间: 2026-02-18 15:06:54

### 测试账号
- 用户名: 13605720328
- 密码: Luyicheng@0505
- 状态: 暂时锁定（需要等待10分钟）

### 相关文件
- 测试脚本: test_api_endpoints.py
- 详细测试: test_api_detailed.py
- 测试报告: logs/api_endpoint_test_report.json

---

**报告生成时间**: 2026-02-18 15:07:29
**报告生成者**: Bug修复专家
