#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高济健康 - 签到及任务自动完成脚本
基于 HAR 抓包分析 (QL-GJ)

功能:
1. 每日签到获取高G金
2. 自动完成浏览任务（逛积分商城、查看省钱卡等）
3. 查询积分余额
4. 查询会员等级

配置方式（环境变量）:
  TOKEN: 必填，bearer token / access_token
  BUSINESS_ID: 商家ID，默认 466606
  STORE_ID: 门店ID，默认 3225031566606
  USER_ID: 用户ID，默认 6070827797166606
  PLATFORM_USER_ID: 平台用户ID，默认 5282553618412798
  UNION_ID: 微信unionId，默认 oWMs41LM9XuGX7eFzhIFIC02dzUc

兼容青龙面板，支持多用户 (使用 & 分隔)
"""

import os
import re
import sys
import json
import time
import hmac
import hashlib
import requests

# ============================================================
# 配置区
# ============================================================

BASE_URL = "https://api.gaojihealth.cn"

# 默认配置（可从环境变量覆盖）
DEFAULT_CONFIG = {
    "businessId": "466606",
    "storeId": "3225031566606",
    "userId": "6070827797166606",
    "platformUserId": "5282553618412798",
    "unionId": "oWMs41LM9XuGX7eFzhIFIC02dzUc",
    "miniOpenId": "optxd5cJn5jH3iBGybYrpCfTV77o",
}

# ============================================================
# 日志工具
# ============================================================

def log(msg, level="INFO"):
    """统一日志输出"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def log_error(msg):
    log(msg, "ERROR")

def log_success(msg):
    log(msg, "SUCCESS")

def log_info(msg):
    log(msg, "INFO")

# ============================================================
# 网络请求工具
# ============================================================

class GaoJiClient:
    """高济健康 API 客户端"""

    def __init__(self, token, config=None):
        self.token = token.strip()
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.session = requests.Session()

        # 设置请求头 - 模拟微信小程序
        self.session.headers.update({
            "Host": "api.gaojihealth.cn",
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": f"bearer {token}",
            "Cookie": f"access_token={token}",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_5 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                          "MicroMessenger/8.0.75(0x18004b42) NetType/4G Language/zh_CN",
            "Referer": "https://servicewechat.com/wx73ec617ea0a6c8e8/1344/page-frame.html",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })

    def _get(self, path, params=None):
        """GET 请求"""
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            return resp.json() if resp.text else {}
        except Exception as e:
            log_error(f"GET {path} 请求失败: {e}")
            return None

    def _post(self, path, data=None):
        """POST 请求"""
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.post(url, json=data or {}, timeout=30)
            return resp.json() if resp.text else {}
        except Exception as e:
            log_error(f"POST {path} 请求失败: {e}")
            return None

    # ============================================================
    # 签到相关
    # ============================================================

    def get_sign_page(self):
        """获取签到页面信息"""
        path = "/fund/api/noauth/appCoupon/findDkSignActivityPage"
        params = {
            "businessId": self.config["businessId"],
            "userId": self.config["userId"],
            "version": "1.4",
        }
        result = self._get(path, params)
        if result and result.get("runFlag"):
            sign_module = result.get("signModule", {})
            base_info = result.get("baseInfoModule", {})
            integral = result.get("integralResponse", {})

            log_info(f"签到页面加载成功")
            log_info(f"当前高G金: {integral.get('currentFund', '未知')}")
            log_info(f"签到任务ID: {sign_module.get('taskId')}")
            log_info(f"签到可得: {base_info.get('fundVal', 0)} 高G金/天")

            # 检查今天是否已签到
            today_sign = None
            for day in sign_module.get("dayList", []):
                if day.get("todayFlag"):
                    today_sign = day
                    break

            if today_sign:
                if today_sign.get("signFlag"):
                    log_info("今日已签到 ✅")
                    return {"signed": True, "data": result}
                else:
                    log_info("今日尚未签到，准备签到...")
                    return {"signed": False, "data": result}
            return {"signed": True, "data": result}
        else:
            log_error("获取签到页面失败")
            return None

    def do_sign(self, task_id=372):
        """执行签到

        根据抓包分析，签到接口通常为 POST 方式。
        如果默认的签到接口无效，请自行抓包补充。
        """
        # 方式1: 尝试签到接口
        sign_paths = [
            "/fund/api/appCoupon/doSign",
            "/fund/api/noauth/appCoupon/doSign",
            "/fund/api/appCoupon/userSign",
            "/fund/api/noauth/appCoupon/userSignIn",
        ]

        for path in sign_paths:
            payload = {
                "taskId": task_id,
                "businessId": int(self.config["businessId"]),
                "userId": self.config["userId"],
                "storeId": int(self.config["storeId"]),
            }
            log_info(f"尝试签到接口: {path}")
            result = self._post(path, payload)
            if result:
                success = result.get("success") or result.get("code") == 200
                if success:
                    msg = result.get("message") or result.get("msg") or "签到成功"
                    log_success(f"签到成功! {msg}")
                    # 签到后获取奖励详情
                    if "content" in result and result["content"]:
                        log_info(f"获得奖励: {result['content']}")
                    return True
                else:
                    msg = result.get("message") or result.get("msg") or "未知"
                    log_info(f"接口返回: {msg}")

        # 方式2: 如果上面的接口都不行，尝试通过 event 方式
        log_info("尝试通过事件接口签到...")
        event_payload = {
            "userId": self.config["userId"],
            "bizType": "dailySignIn",
            "status": 1,
            "businessId": int(self.config["businessId"]),
            "storeId": int(self.config["storeId"]),
        }
        result = self._post("/gulosity/api/dkUserEvent/createDkUserEvent", event_payload)
        if result and result.get("success"):
            log_success("通过事件接口签到成功!")
            return True

        log_error("所有签到接口均失败，请手动抓包确认签到接口")
        return False

    # ============================================================
    # 任务相关
    # ============================================================

    def get_sign_page_full(self):
        """获取完整签到页面（含任务列表）"""
        return self.get_sign_page()

    def get_user_achievement(self):
        """获取用户成就/等级信息"""
        path = "/gulosity/api/dkUserAchievement/getUserAchievement"
        payload = {
            "businessId": self.config["businessId"],
            "userId": self.config["userId"],
            "platformUserId": self.config["platformUserId"],
            "queryUserLevelNewVersion": True,
            "version": "3.0",
            "storeId": int(self.config["storeId"]),
        }
        result = self._post(path, payload)
        if result and result.get("id"):
            log_info(f"会员等级: {result.get('levelName', '未知')} "
                     f"(Lv.{result.get('userLevel', 0)}, "
                     f"积分: {result.get('score', 0)})")
            return result
        return None

    def get_user_fund(self):
        """获取用户高G金余额"""
        path = "/fund/api/fundAccounts/getCurrentFundV2"
        params = {
            "businessId": self.config["businessId"],
            "storeId": self.config["storeId"],
        }
        result = self._get(path, params)
        if result:
            log_info(f"高G金余额: {result.get('currentFund', '未知')}")
            return result
        return None

    def get_user_info(self):
        """获取用户详情"""
        path = "/uaa/api/userbaseinfo/userDetail"
        params = {
            "storeId": self.config["storeId"],
            "maskingFlag": "false",
        }
        result = self._get(path, params)
        if result:
            log_info(f"用户信息加载成功")
            return result
        return None

    def get_tasks(self):
        """获取签到页面的任务列表"""
        result = self.get_sign_page()
        if result and result.get("data"):
            task_module = result["data"].get("taskModule", {})
            tasks = task_module.get("integralTaskList", [])
            if tasks:
                log_info(f"获取到 {len(tasks)} 个可完成任务:")
                for task in tasks:
                    log_info(f"  - {task.get('name', '未知')} "
                             f"(奖励: {task.get('prizeInfo', '?')} 积分, "
                             f"状态: {'已完成' if task.get('status') == 1 else '未完成'}, "
                             f"剩余次数: {task.get('leftTimes', 0)})")
            else:
                log_info("当前无可完成的任务")
            return tasks
        return []

    def complete_browse_task(self, task):
        """完成浏览任务

        浏览任务通过上报事件来完成。
        根据抓包分析，浏览任务使用 eventKey 作为标识。
        """
        task_id = task.get("taskId")
        task_name = task.get("name", "未知任务")
        biz_type = task.get("bizType", "browsePage")
        event_key = task.get("eventKey", "")
        browse_page_id = task.get("browsePageId", "")
        browse_page_url = task.get("browsePageUrl", "")

        log_info(f"开始完成任务: {task_name} (taskId={task_id})")

        # 方式1: 通过事件上报完成浏览任务
        # 这是 dkUserEvent 的创建接口
        event_paths = [
            "/gulosity/api/dkUserEvent/createDkUserEvent",
            "/gulosity/api/dkUserEvent/saveOrUpdate",
            "/gulosity/api/dkUserEvent/addUserEvent",
        ]

        for path in event_paths:
            payload = {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "eventKey": event_key,
                "status": 1,
                "platformUserId": self.config["platformUserId"],
            }
            result = self._post(path, payload)
            if result:
                success = result.get("success") or result.get("code") == 200
                if success:
                    log_success(f"任务 [{task_name}] 完成! ✅")
                    return True

        # 方式2: 尝试通过 fund/appCoupon 接口完成
        browse_paths = [
            "/fund/api/appCoupon/browsePage",
            "/fund/api/noauth/appCoupon/browsePage",
            "/fund/api/appCoupon/completeTask",
        ]

        for path in browse_paths:
            payload = {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }
            result = self._post(path, payload)
            if result:
                success = result.get("success") or result.get("code") == 200
                if success:
                    log_success(f"任务 [{task_name}] 完成! ✅")
                    return True

        log_error(f"任务 [{task_name}] 完成失败，请手动抓包确认接口")
        return False

    def complete_all_tasks(self):
        """完成所有可完成的任务"""
        tasks = self.get_tasks()
        if not tasks:
            log_info("没有需要完成的任务")
            return

        completed = 0
        for task in tasks:
            if task.get("status") == 1:
                log_info(f"任务 [{task.get('name', '未知')}] 已完成，跳过")
                continue
            if task.get("leftTimes", 0) <= 0:
                log_info(f"任务 [{task.get('name', '未知')}] 无剩余次数，跳过")
                continue

            if self.complete_browse_task(task):
                completed += 1
            time.sleep(1)  # 间隔1秒，避免请求过快

        log_success(f"完成 {completed}/{len(tasks)} 个任务")

    # ============================================================
    # 综合查询
    # ============================================================

    def query_all_info(self):
        """查询所有用户信息"""
        log_info("=" * 40)
        log_info("查询用户信息...")
        log_info("=" * 40)

        self.get_user_info()
        self.get_user_fund()
        self.get_user_achievement()

    # ============================================================
    # 主流程
    # ============================================================

    def run(self):
        """主运行流程"""
        log_info("=" * 40)
        log_info("高济健康 - 签到任务自动执行")
        log_info("=" * 40)

        # 1. 查询用户信息
        self.query_all_info()

        # 2. 签到
        log_info("")
        log_info("=" * 40)
        log_info("执行签到...")
        log_info("=" * 40)
        sign_result = self.get_sign_page()
        if sign_result and not sign_result.get("signed"):
            self.do_sign()
        elif sign_result and sign_result.get("signed"):
            log_info("今日已签到，跳过")

        # 3. 完成任务
        log_info("")
        log_info("=" * 40)
        log_info("执行任务...")
        log_info("=" * 40)
        self.complete_all_tasks()

        # 4. 最终查询
        log_info("")
        log_info("=" * 40)
        log_info("执行结果汇总")
        log_info("=" * 40)
        self.get_user_fund()

        log_success("所有任务执行完毕!")


# ============================================================
# 多用户支持
# ============================================================

def parse_tokens(token_str):
    """解析多用户 token，支持 & 分隔"""
    if not token_str:
        return []
    # 支持 & 或换行分隔
    tokens = re.split(r'[&\n]', token_str)
    return [t.strip() for t in tokens if t.strip()]


def run_user(token, config_override=None):
    """运行单个用户"""
    client = GaoJiClient(token, config_override)
    try:
        client.run()
    except Exception as e:
        log_error(f"用户执行异常: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# 主入口
# ============================================================

def main():
    # 从环境变量读取配置
    token_str = os.environ.get("TOKEN") or os.environ.get("GJ_TOKEN") or ""
    if not token_str:
        log_error("未设置 TOKEN 环境变量！")
        log_info("请设置 TOKEN 环境变量为你的 bearer token")
        log_info("多用户请用 & 分隔多个 token")
        log_info("")
        log_info("示例 (bash):")
        log_info("  export TOKEN=         log_info(\"今日已签到，跳过\")\n\n        # 3. 完成任务\n        log_info(\"\")\n        log_info(\"=\" * 40)\n        log_info(\"执行任务...\")\n        log_info(\"=\" * 40)\n        self.complete_all_tasks()\n\n        # 4. 最终查询\n        log_info(\"\")\n        log_info(\"=\" * 40)\n        log_info(\"执行结果汇总\")\n        log_info(\"=\" * 40)\n        self.get_user_fund()\n\n        log_success(\"所有任务执行完毕!\")\n\n\n# ============================================================\n# 多用户支持\n# ============================================================\n\ndef parse_tokens(token_str):\n    \"\"\"解析多用户 token，支持 & 分隔\"\"\"\n    if not token_str:\n        return []\n    # 支持 & 或换行分隔\n    tokens = re.split(r'[&\\n]', token_str)\n    return [t.strip() for t in tokens if t.strip()]\n\n\ndef run_user(token, config_override=None):\n    \"\"\"运行单个用户\"\"\"\n    client = GaoJiClient(token, config_override)\n    try:\n        client.run()\n    except Exception as e:\n        log_error(f\"用户执行异常: {e}\")\n        import traceback\n        traceback.print_exc()\n\n\n# ============================================================\n# 主入口\n# ============================================================\n\ndef main():\n    # 从环境变量读取配置\n    token_str = os.environ.get(\"TOKEN\") or os.environ.get(\"GJ_TOKEN\") or \"\"\n    if not token_str:\n        log_error(\"未设置 TOKEN 环境变量！\")\n        log_info(\"请设置 TOKEN 环境变量为你的 bearer token\")\n        log_info(\"多用户请用 & 分隔多个 token\")\n        log_info(\"\")\n        log_info(\"示例 (bash):\")\n        log_info(\"  export TOKEN=\\\\"your_token_here\\\"\")\n        log_info(\"  export TOKEN=\\\\"token1&token2&token3\\\"\")\n        log_info(\"\")\n        log_info(\"示例 (青龙面板):\")\n        log_info(\"  在环境变量中添加 GJ_TOKEN 或 TOKEN\")\n        sys.exit(1)\n\n    # 自定义配置\n    config_override = {}\n    for key in [\"businessId\", \"storeId\", \"userId\", \"platformUserId\", \"unionId\"]:\n        env_key = f\"GJ_{key.upper()}\"\n        if env_key in os.environ:\n            config_override[key] = os.environ[env_key]\n\n    # 解析多用户\n    tokens = parse_tokens(token_str)\n    log_info(f\"检测到 {len(tokens)} 个用户\")\n\n    for i, token in enumerate(tokens):\n        log_info(\"\")\n        log_info(\"#\" * 50)\n        log_info(f\"用户 {i + 1}/{len(tokens)}\")\n        log_info(\"#\" * 50)\n        run_user(token, config_override)\n\n    log_info(\"\")\n    log_info(\"=\" * 40)\n    log_success(f\"全部 {len(tokens)} 个用户执行完毕!\")\n\n\nif __name__ == \"__main__\":\n    main()\n"}]