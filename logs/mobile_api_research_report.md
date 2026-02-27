
# 阿贝云移动端API研究报告

**研究时间**: 2026-02-18 15:45:24
**测试账号**: 13605720328
**移动端站点**: https://m.abeiyun.com
**桌面端站点**: https://www.abeiyun.com

---

## 1. API端点对比

### 移动端API端点
- **基础URL**: `https://m.abeiyun.com/api`
- **登录API**: `https://m.abeiyun.com/api/login.php`
- **VPS API**: `https://m.abeiyun.com/api/vps.php`

### 桌面端API端点
- **基础URL**: `https://api.abeiyun.com/www`
- **登录API**: `https://api.abeiyun.com/www/login.php`
- **VPS API**: `https://api.abeiyun.com/www/vps.php`

---

## 2. 登录API对比

### 移动端登录
- **URL**: `https://m.abeiyun.com/api/login.php`
- **方法**: POST
- **参数**:
  ```json
  {
    "cmd": "login",
    "id_mobile": "手机号",
    "password": "密码"
  }
  ```

### 桌面端登录
- **URL**: `https://api.abeiyun.com/www/login.php`
- **方法**: POST
- **参数**:
  ```json
  {
    "cmd": "login",
    "id_mobile": "手机号",
    "password": "密码"
  }
  ```

---

## 3. 延期列表API对比

### 移动端
- **URL**: `https://m.abeiyun.com/api/vps.php`
- **方法**: POST
- **测试命令**: free_delay_list, vps_list, delay_list, get_delay_list

### 桌面端
- **URL**: `https://api.abeiyun.com/www/vps.php`
- **方法**: POST
- **可用命令**: vps_list

---

## 4. 延期提交API对比

### 移动端
- **URL**: `https://m.abeiyun.com/api/vps.php`
- **方法**: POST
- **测试命令**: free_delay, delay_submit, submit_delay, apply_delay

### 桌面端
- **URL**: `https://api.abeiyun.com/www/vps.php`
- **方法**: POST
- **测试命令**: free_delay

---

## 5. 主要发现

### API端点差异
1. **基础URL不同**:
   - 移动端: `https://m.abeiyun.com/api`
   - 桌面端: `https://api.abeiyun.com/www`

2. **请求头差异**:
   - 移动端使用移动浏览器User-Agent
   - 桌面端使用桌面浏览器User-Agent

3. **Origin和Referer**:
   - 移动端: `https://m.abeiyun.com`
   - 桌面端: `https://www.abeiyun.com`

---

## 6. 建议

1. **移动端API可能更简单**: 移动端站点通常使用更简单的API，可能直接返回JSON数据
2. **需要实际测试**: 由于测试账号没有服务器，无法完整测试延期功能
3. **截图上传方式**: 需要进一步研究移动端和桌面端的截图上传方式差异

---

**报告生成时间**: 2026-02-18 15:45:24
