# 阿贝云移动端API文档

**生成时间**: 自动生成
**来源**: Vue.js应用源码分析
**站点**: https://m.abeiyun.com

---

## 发现的API端点

### 完整URL端点

```
https://api.abeiyun.com/weixin/pay/jsapi.php
https://api.abeiyun.com/www/caiwu.php
https://api.abeiyun.com/www/domain.php
https://api.abeiyun.com/www/gd.php
https://api.abeiyun.com/www/haomiao.php
https://api.abeiyun.com/www/login.php
https://api.abeiyun.com/www/login.php?cmd=logout
https://api.abeiyun.com/www/mianbeian.php
https://api.abeiyun.com/www/reg.php
https://api.abeiyun.com/www/reg.php?cmd=img_yzm&rnd=
https://api.abeiyun.com/www/renew.php
https://api.abeiyun.com/www/reset_pwd.php
https://api.abeiyun.com/www/upgrade.php
https://api.abeiyun.com/www/user.php
https://api.abeiyun.com/www/vhost.php
https://api.abeiyun.com/www/vps.php
https://api.abeiyun.com/www/yzm.php
https://api.abeiyun.com/www/yzm.php?rnd=
https://api.abeiyun.com/www/yzm.php?yzm_type=num&rnd=
https://s96.cnzz.com/z_stat.php
```

### API路径

### 其他路径

```
activeOpacity
align
alignWithLabel
alwaysShowContent
animation
animationDuration
animationDurationUpdate
animationEasing
animationType
areaColor
aspectScale
avoidLabelOverlap
axisExpandCenter
axisExpandCount
axisExpandDebounce
axisExpandRate
axisExpandSlideTriggerArea
axisExpandTriggerOn
axisExpandWidth
axisExpandWindow
```

---

## 推测的API端点

基于Vue.js应用结构和桌面端API，推测移动端使用的API端点：

### 登录API
- **URL**: `https://api.abeiyun.com/www/login.php`
- **方法**: POST
- **参数**:
  - `cmd`: login
  - `id_mobile`: 手机号
  - `password`: 密码

### VPS列表API
- **URL**: `https://api.abeiyun.com/www/vps.php`
- **方法**: POST
- **参数**:
  - `cmd`: vps_list
  - `page`: 页码

### 延期申请API
- **URL**: `https://api.abeiyun.com/www/vps.php`
- **方法**: POST
- **参数**:
  - `cmd`: free_delay
  - `id`: 服务器ID
  - `url`: 发帖地址
  - `img`: 截图文件

---

## 配置信息

- **config**: N/A = n
- **config**: N/A = l
- **config**: N/A = s
- **config**: N/A = s
- **config**: N/A = t
- **config**: N/A = b
- **config**: N/A = m
- **config**: N/A = v
- **config**: N/A = e
- **config**: N/A = p
- **config**: N/A = n
- **config**: N/A = s
- **config**: N/A = i
- **config**: N/A = t
- **config**: N/A = e
- **config**: N/A = n
- **config**: N/A = e
- **config**: N/A = h
- **config**: N/A = e
- **config**: N/A = ot
- **config**: N/A = h
- **config**: N/A = d
- **config**: N/A = e
- **config**: N/A = y
- **config**: N/A = e
- **config**: N/A = h
- **config**: N/A = t
- **config**: N/A = r
- **config**: N/A = g
- **config**: N/A = t
- **config**: N/A = y
- **config**: N/A = i
- **config**: N/A = r
- **config**: N/A = f
- **config**: N/A = l
- **config**: N/A = n
- **config**: N/A = o
- **config**: N/A = e
- **config**: N/A = n
- **config**: N/A = t
- **config**: N/A = e
- **config**: N/A = i
- **config**: N/A = n
- **config**: N/A = r
- **config**: N/A = n
- **config**: N/A = s
- **config**: N/A = s
- **config**: N/A = g
- **config**: N/A = h
- **config**: N/A = l

---

## 注意事项

1. 移动端站点使用Vue.js单页应用架构
2. API端点可能与桌面端共享
3. 需要正确处理UTF-8 BOM标记
4. 所有API需要session_id cookie

---

**文档生成时间**: 自动生成
