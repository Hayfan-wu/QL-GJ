# QL-GJ

高济健康（高G金）签到及任务自动完成脚本

## 功能

- 每日自动签到获取高G金
- 自动完成浏览任务（逛积分商城、查看省钱卡等）
- 查询积分余额与会员等级
- 多用户支持
- 兼容青龙面板

## 使用方法

### 环境变量配置

| 变量名 | 说明 | 必填 | 默认值 |
|--------|------|------|--------|
| `TOKEN` 或 `GJ_TOKEN` | 认证 token（bearer token） | 是 | - |
| `GJ_BUSINESSID` | 商家ID | 否 | 466606 |
| `GJ_STOREID` | 门店ID | 否 | 3225031566606 |
| `GJ_USERID` | 用户ID | 否 | 6070827797166606 |
| `GJ_PLATFORMUSERID` | 平台用户ID | 否 | 5282553618412798 |
| `GJ_UNIONID` | 微信 unionId | 否 | oWMs41LM9XuGX7eFzhIFIC02dzUc |

### 多用户

多用户使用 `&` 分隔多个 token：
```
TOKEN="token1&token2&token3"
```

### 青龙面板

1. 创建定时任务，执行命令：`python3 gaoji_health.py`
2. 设置环境变量 `GJ_TOKEN` 或 `TOKEN`
3. 建议每天执行一次

### 本地运行
```bash
pip install requests
TOKEN="your_token_here" python3 gaoji_health.py
```

## 抓包说明

本脚本基于微信小程序「高济健康」的 HAR 抓包分析编写。

主要接口：
- 签到页面：`GET /fund/api/noauth/appCoupon/findDkSignActivityPage`
- 用户等级：`POST /gulosity/api/dkUserAchievement/getUserAchievement`
- 高G金余额：`GET /fund/api/fundAccounts/getCurrentFundV2`
- 用户详情：`GET /uaa/api/userbaseinfo/userDetail`
- 用户事件列表：`POST /gulosity/api/dkUserEvent/findDkUserEventList`

如果签到接口失效，请重新抓包获取最新的签到接口地址。

## TOKEN 获取方法

1. 打开微信小程序「高济健康」
2. 使用抓包工具（如 Charles、Fiddler、Stream）
3. 过滤 `api.gaojihealth.cn` 的请求
4. 查看任意请求头中的 `Authorization: bearer <token>` 或 `Cookie: access_token=<token>`
