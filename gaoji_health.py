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

注意：本脚本已根据抓包数据修复了查询接口，但签到和任务完成接口
在提供的 HAR 中未捕获到实际请求。脚本内置了多组候选接口，如果
均不可用，需要重新抓包获取实际接口地址。
"""

import os
import re
import sys
import json
import time
import requests

BASE_URL = "https://api.gaojihealth.cn"

DEFAULT_CONFIG = {
    "businessId": "466606",
    "storeId": "3225031566606",
    "userId": "6070827797166606",
    "platformUserId": "5282553618412798",
    "unionId": "oWMs41LM9XuGX7eFzhIFIC02dzUc",
    "miniOpenId": "optxd5cJn5jH3iBGybYrpCfTV77o",
}


def log(msg, level="INFO"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def log_error(msg):
    log(msg, "ERROR")


def log_success(msg):
    log(msg, "SUCCESS")


def log_info(msg):
    log(msg, "INFO")


class GaoJiClient:

    def __init__(self, token, config=None):
        self.token = token.strip()
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.session = requests.Session()
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
        })

    def _get(self, path, params=None):
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            return resp.json() if resp.text else {}
        except Exception as e:
            log_error(f"GET {path} 失败: {e}")
            return None

    def _post(self, path, data=None):
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.post(url, json=data or {}, timeout=30)
            return resp.json() if resp.text else {}
        except Exception as e:
            log_error(f"POST {path} 失败: {e}")
            return None

    def get_sign_page(self):
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
            log_info(f"当前高G金: {integral.get('currentFund', '未知')}")
            log_info(f"签到任务ID: {sign_module.get('taskId')}")
            log_info(f"签到可得: {base_info.get('fundVal', 0)} 高G金/天")
            for day in sign_module.get("dayList", []):
                if day.get("todayFlag"):
                    if day.get("signFlag"):
                        log_info("今日已签到")
                        return {"signed": True, "data": result}
                    else:
                        log_info("今日尚未签到，准备签到...")
                        return {"signed": False, "data": result}
            return {"signed": True, "data": result}
        else:
            log_error("获取签到页面失败")
            return None

    def do_sign(self, task_id=372):
        """执行签到 - 尝试多组候选接口"""
        # 候选签到接口列表（基于常见微信小程序签到模式）
        sign_candidates = [
            # fund 模块
            {"path": "/fund/api/appCoupon/doSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/noauth/appCoupon/doSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/appCoupon/signIn", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/noauth/appCoupon/signIn", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/appCoupon/userSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/noauth/appCoupon/userSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/appCoupon/sign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/noauth/appCoupon/sign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/dkSign/doSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/fund/api/sign/doSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            # gulosity 模块
            {"path": "/gulosity/api/dkUserEvent/createDkUserEvent", "body": {"userId": self.config["userId"], "bizType": "dailySignIn", "status": 1, "businessId": int(self.config["businessId"]), "storeId": int(self.config["storeId"])}},
            {"path": "/gulosity/api/dkUserEvent/addUserEvent", "body": {"userId": self.config["userId"], "bizType": "dailySignIn", "status": 1, "businessId": int(self.config["businessId"]), "storeId": int(self.config["storeId"])}},
            {"path": "/gulosity/api/dkUserEvent/saveOrUpdate", "body": {"userId": self.config["userId"], "bizType": "dailySignIn", "status": 1, "businessId": int(self.config["businessId"]), "storeId": int(self.config["storeId"])}},
            # gaea 模块
            {"path": "/gaea/api/appCoupon/doSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
            {"path": "/gaea/api/noauth/appCoupon/doSign", "body": {"taskId": task_id, "businessId": int(self.config["businessId"]), "userId": self.config["userId"], "storeId": int(self.config["storeId"])}},
        ]

        for candidate in sign_candidates:
            path = candidate["path"]
            body = candidate["body"]
            log_info(f"尝试签到: {path}")
            result = self._post(path, body)
            if result is not None:
                # 检查成功标志
                code = result.get("code")
                success = result.get("success")
                msg = result.get("message") or result.get("msg") or ""
                if success or code == 200:
                    log_success(f"签到成功! {msg}")
                    return True
                log_info(f"返回 [{code}]: {msg}")

        log_error("所有候选签到接口均失败，请手动抓包确认签到接口")
        return False

    def get_user_achievement(self):
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
                     f"(Lv.{result.get('userLevel', 0)}, 积分: {result.get('score', 0)})")
            return result
        return None

    def get_user_fund(self):
        """获取用户高G金余额 - 修复字段名"""
        path = "/fund/api/fundAccounts/getCurrentFundV2"
        params = {"businessId": self.config["businessId"], "storeId": self.config["storeId"]}
        result = self._get(path, params)
        if result:
            # 注意：接口返回字段名为 fund，不是 currentFund
            fund = result.get("fund", result.get("currentFund", "未知"))
            log_info(f"高G金余额: {fund}")
            return result
        return None

    def get_user_info(self):
        path = "/uaa/api/userbaseinfo/userDetail"
        params = {"storeId": self.config["storeId"], "maskingFlag": "false"}
        result = self._get(path, params)
        if result:
            name = result.get("name", "未知")
            phone = result.get("phone", "")
            log_info(f"用户信息: {name} ({phone})")
            return result
        return None

    def get_tasks(self):
        result = self.get_sign_page()
        if result and result.get("data"):
            tasks = result["data"].get("taskModule", {}).get("integralTaskList", [])
            if tasks:
                log_info(f"获取到 {len(tasks)} 个可完成任务:")
                for task in tasks:
                    log_info(f"  - {task.get('name', '未知')} "
                             f"(奖励: {task.get('prizeInfo', '?')} 积分, "
                             f"状态: {'已完成' if task.get('status') == 1 else '未完成'}, "
                             f"剩余: {task.get('leftTimes', 0)}次)")
            return tasks
        return []

    def complete_browse_task(self, task):
        """完成浏览任务 - 尝试多组候选接口"""
        task_id = task.get("taskId")
        task_name = task.get("name", "未知任务")
        biz_type = task.get("bizType", "browsePage")
        event_key = task.get("eventKey", "")
        browse_page_id = task.get("browsePageId", "")
        browse_page_url = task.get("browsePageUrl", "")
        log_info(f"开始完成任务: {task_name}")

        # 候选任务完成接口
        task_candidates = [
            # gulosity 事件模块
            {"path": "/gulosity/api/dkUserEvent/createDkUserEvent", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "eventKey": event_key,
                "status": 1,
                "platformUserId": self.config["platformUserId"],
            }},
            {"path": "/gulosity/api/dkUserEvent/addUserEvent", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "eventKey": event_key,
                "status": 1,
                "platformUserId": self.config["platformUserId"],
            }},
            {"path": "/gulosity/api/dkUserEvent/saveOrUpdate", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "eventKey": event_key,
                "status": 1,
                "platformUserId": self.config["platformUserId"],
            }},
            # fund 模块
            {"path": "/fund/api/appCoupon/completeTask", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }},
            {"path": "/fund/api/noauth/appCoupon/completeTask", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }},
            {"path": "/fund/api/appCoupon/doTask", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }},
            {"path": "/fund/api/noauth/appCoupon/doTask", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }},
            {"path": "/fund/api/appCoupon/browsePage", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }},
            {"path": "/fund/api/noauth/appCoupon/browsePage", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
                "pageId": browse_page_id,
                "pageUrl": browse_page_url,
            }},
            # gaea 模块
            {"path": "/gaea/api/appCoupon/completeTask", "body": {
                "userId": self.config["userId"],
                "businessId": int(self.config["businessId"]),
                "storeId": int(self.config["storeId"]),
                "taskId": task_id,
                "bizType": biz_type,
            }},
        ]

        for candidate in task_candidates:
            path = candidate["path"]
            body = candidate["body"]
            result = self._post(path, body)
            if result is not None:
                code = result.get("code")
                success = result.get("success")
                msg = result.get("message") or result.get("msg") or ""
                if success or code == 200:
                    log_success(f"任务 [{task_name}] 完成!")
                    return True
                log_info(f"  {path} 返回 [{code}]: {msg}")

        log_error(f"任务 [{task_name}] 完成失败，请手动抓包确认接口")
        return False

    def complete_all_tasks(self):
        tasks = self.get_tasks()
        if not tasks:
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
            time.sleep(1)
        log_success(f"完成 {completed}/{len(tasks)} 个任务")

    def run(self):
        log_info("=" * 40)
        log_info("高济健康 - 签到任务自动执行")
        log_info("=" * 40)
        self.get_user_info()
        self.get_user_fund()
        self.get_user_achievement()
        log_info("")
        log_info("=" * 40)
        log_info("执行签到...")
        log_info("=" * 40)
        sign_result = self.get_sign_page()
        if sign_result and not sign_result.get("signed"):
            self.do_sign()
        elif sign_result and sign_result.get("signed"):
            log_info("今日已签到，跳过")
        log_info("")
        log_info("=" * 40)
        log_info("执行任务...")
        log_info("=" * 40)
        self.complete_all_tasks()
        log_info("")
        log_info("=" * 40)
        log_info("执行结果汇总")
        log_info("=" * 40)
        self.get_user_fund()
        log_success("所有任务执行完毕!")


def parse_tokens(token_str):
    if not token_str:
        return []
    tokens = re.split(r'[&\n]', token_str)
    return [t.strip() for t in tokens if t.strip()]


def run_user(token, config_override=None):
    client = GaoJiClient(token, config_override)
    try:
        client.run()
    except Exception as e:
        log_error(f"用户执行异常: {e}")
        import traceback
        traceback.print_exc()


def main():
    token_str = os.environ.get("TOKEN") or os.environ.get("GJ_TOKEN") or ""
    if not token_str:
        log_error("未设置 TOKEN 环境变量！")
        log_info("请设置 TOKEN 环境变量为你的 bearer token")
        log_info("多用户请用 & 分隔")
        sys.exit(1)
    config_override = {}
    for key in ["businessId", "storeId", "userId", "platformUserId", "unionId"]:
        env_key = f"GJ_{key.upper()}"
        if env_key in os.environ:
            config_override[key] = os.environ[env_key]
    tokens = parse_tokens(token_str)
    log_info(f"检测到 {len(tokens)} 个用户")
    for i, token in enumerate(tokens):
        log_info("")
        log_info("#" * 50)
        log_info(f"用户 {i + 1}/{len(tokens)}")
        log_info("#" * 50)
        run_user(token, config_override)
    log_success(f"全部 {len(tokens)} 个用户执行完毕!")


if __name__ == "__main__":
    main()