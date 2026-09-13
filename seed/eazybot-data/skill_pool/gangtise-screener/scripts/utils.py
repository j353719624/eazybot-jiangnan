import os
import sys
import json
import datetime
from typing import Dict, List, Any, NoReturn
import requests

GTS_AUTHORIZATION_PATH = os.getenv("GTS_AUTHORIZATION_PATH",
                                   os.path.join(os.path.abspath(os.path.dirname(__file__)), ".authorization"))
GTS_ACCESS_KEY = os.getenv("GTS_ACCESS_KEY", None)
GTS_SECRET_KEY = os.getenv("GTS_SECRET_KEY", None)

# 通过 ak/sk 获取 临时 authorization

DEPLOY_ENV = os.getenv("DEPLOY_ENV", "local")
if DEPLOY_ENV == "dev":
    AUTHORIZATION_URL = "http://10.78.10.43:30901/application/auth/oauth/open/loginV2"
elif DEPLOY_ENV == "test":
    AUTHORIZATION_URL = "http://10.78.10.43:30901/application/auth/oauth/open/loginV2"
else:
    # prod / local / 未识别的取值一律走线上，避免 AUTHORIZATION_URL 未定义
    AUTHORIZATION_URL = "https://openapi.gangtise.com/application/auth/oauth/open/loginV2"


def get_authorization(ak: str, sk: str):
    payload = {
        "accessKey": ak,
        "secretKey": sk
    }
    response = requests.post(AUTHORIZATION_URL, json=payload)
    if response.status_code != 200 or not response.json().get("state", True):
        print(f"获取 authorization 失败, 错误信息: {response.text}")
        return None, None, None, None
    try:
        data = response.json()["data"]
        uid = str(data["uid"]) if data.get("uid") else None
        tenant_id = str(data["tenantId"]) if data.get("tenantId") else None
        product_code = str(data.get("productCode", 10018))
        return data["accessToken"], uid, tenant_id, product_code
    except Exception as e:
        print(f"解析 authorization 响应失败, 错误信息: {e}")
        return None, None, None, None


GTS_AUTHORIZATION = None
GTS_UID = None
GTS_TENANTID = None
GTS_PRODUCTCODE = None
if GTS_ACCESS_KEY and GTS_SECRET_KEY:
    GTS_AUTHORIZATION, GTS_UID, GTS_TENANTID, GTS_PRODUCTCODE = get_authorization(GTS_ACCESS_KEY, GTS_SECRET_KEY)
elif os.path.exists(GTS_AUTHORIZATION_PATH):
    with open(GTS_AUTHORIZATION_PATH, "r", encoding="utf-8") as f:
        content = json.load(f)
        if content.get("authorization", None):
            GTS_AUTHORIZATION = content["authorization"] if content["authorization"].startswith(
                "Bearer ") else "Bearer " + content["authorization"]
        elif content.get("accessKey", None) and content.get("secretKey", None):
            GTS_AUTHORIZATION, GTS_UID, GTS_TENANTID, GTS_PRODUCTCODE = get_authorization(content["accessKey"],
                                                                                          content["secretKey"])
        elif content.get("accessKey", None) and content.get("secretAccessKey", None):
            GTS_AUTHORIZATION, GTS_UID, GTS_TENANTID, GTS_PRODUCTCODE = get_authorization(content["accessKey"],
                                                                                          content["secretAccessKey"])
        else:
            GTS_AUTHORIZATION = None

HEADERS_EXTRA = {}
if GTS_UID:
    HEADERS_EXTRA["uid"] = GTS_UID
if GTS_TENANTID:
    HEADERS_EXTRA["tenantid"] = GTS_TENANTID
if GTS_PRODUCTCODE:
    HEADERS_EXTRA["productcode"] = GTS_PRODUCTCODE

GTS_SAVE_FILE = os.getenv("GTS_SAVE_FILE", False)
GTS_SAVE_EXTENSION = os.getenv("GTS_SAVE_EXTENSION", "json")

GANGTISE_INDICATOR_DOMAIN = os.getenv(
    "GANGTISE_INDICATOR_DOMAIN",
    "https://openapi.gangtise.com/application/open-indicator"
).rstrip("/")
GANGTISE_REFERENCE_DOMAIN = os.getenv(
    "GANGTISE_REFERENCE_DOMAIN",
    "https://openapi.gangtise.com/application/open-reference",
).rstrip("/")
GANGTISE_QUOTE_DOMAIN = os.getenv(
    "GANGTISE_QUOTE_DOMAIN",
    "https://openapi.gangtise.com/application/open-quote",
).rstrip("/")
INDICATOR_URL = os.getenv("INDICATOR_URL", f'{GANGTISE_INDICATOR_DOMAIN}/EDE/search')  # 查询指标及指标参数URL
INDICATOR_STOCK_URL = os.getenv("INDICATOR_STOCK_URL", f'{GANGTISE_INDICATOR_DOMAIN}/screener')  # 指标选股URL
SECTOR_SEARCH_URL = os.getenv("SECTOR_SEARCH_URL", f"{GANGTISE_REFERENCE_DOMAIN}/sectors/search")
SECURITIES_SEARCH_URL = os.getenv(
    "SECURITIES_SEARCH_URL", f"{GANGTISE_REFERENCE_DOMAIN}/securities/search"
)
QUOTE_URL = os.getenv("QUOTE_URL", f"{GANGTISE_QUOTE_DOMAIN}/kline/daily")
HTTP_TIMEOUT = 600


def die(message: str, code: int = 1) -> NoReturn:
    """Print error message and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(code)


WORK_PATH = os.getenv("WORK_PATH", None)
if WORK_PATH:
    gangtise_workspace_path = WORK_PATH
elif DEPLOY_ENV == "local":
    def _find_openclaw_root():
        """向上遍历目录直到找到 .openclaw，返回其上级目录作为执行目录"""
        path = os.path.abspath(os.path.dirname(__file__))
        openclaw_dir_got = False
        while path != os.path.dirname(path):
            dir_name = os.path.basename(path)
            if dir_name in (".openclaw"):
                openclaw_dir_got = True
                return os.path.abspath(path)
            path = os.path.dirname(path)
        path = os.path.abspath(os.path.dirname(__file__))
        if not openclaw_dir_got:
            openclaw_dir_got = False
            while path != os.path.dirname(path):
                dir_name = os.path.basename(path)
                if dir_name in (".agent"):
                    openclaw_dir_got = True
                    return os.path.abspath(path)
                path = os.path.dirname(path)
        path = os.path.abspath(os.path.dirname(__file__))
        if not openclaw_dir_got:
            openclaw_dir_got = False
            while path != os.path.dirname(path):
                dir_name = os.path.basename(path)
                if dir_name in ("workspace"):
                    openclaw_dir_got = True
                    return os.path.abspath(path)
                path = os.path.dirname(path)
        path = os.path.abspath(os.path.dirname(__file__))
        if not openclaw_dir_got:
            openclaw_dir_got = False
            while path != os.path.dirname(path):
                dir_name = os.path.basename(path)
                if dir_name in ("skills"):
                    openclaw_dir_got = True
                    return os.path.abspath(os.path.dirname(path))
                path = os.path.dirname(path)
        return os.path.abspath(os.getcwd())


    openclaw_root = _find_openclaw_root()
    if openclaw_root.endswith("workspace"):
        gangtise_workspace_path = os.path.join(openclaw_root, "gangtise")
    else:
        gangtise_workspace_path = os.path.join(openclaw_root, "workspace", "gangtise")
else:
    gangtise_workspace_path = "/opt/data/workspace/default"

if not os.path.exists(gangtise_workspace_path):
    os.makedirs(gangtise_workspace_path, exist_ok=True)

usage_dir = os.path.join(gangtise_workspace_path, ".usage")
if not os.path.exists(usage_dir):
    os.makedirs(usage_dir, exist_ok=True)

file_dir = os.path.join(gangtise_workspace_path, "files")
if not os.path.exists(file_dir):
    os.makedirs(file_dir, exist_ok=True)


def add_usages(usages_list: List[Dict[str, Any]]):
    usages = {}
    for usages_item in usages_list:
        if len(usages_item) == 0:
            continue
        for k, v in usages_item.items():
            if k not in usages:
                usages[k] = v
            else:
                usages[k] = usages[k] + v
    return usages


def save_data_csv(
    records: List[Dict[str, Any]],
    method_name: str = "screener",
    module_name: str = "screener",
) -> str:
    """将结果落盘为 CSV（对齐 gangtise-data format_response 的 data 路径），返回绝对路径。"""
    import csv
    import time

    if not records:
        raise ValueError("records 不能为空")

    process_dir = os.path.join(gangtise_workspace_path, method_name)
    if not os.path.exists(process_dir):
        os.makedirs(process_dir, exist_ok=True)

    now = datetime.datetime.now().strftime("%H%M%S")
    process_path = os.path.join(process_dir, f"{module_name}_{now}.csv")
    max_retries = 10
    while os.path.exists(process_path) and max_retries > 0:
        time.sleep(1)
        now = datetime.datetime.now().strftime("%H%M%S")
        process_path = os.path.join(process_dir, f"{module_name}_{now}.csv")
        max_retries -= 1
    if max_retries == 0:
        raise RuntimeError("文件存储系统繁忙，请稍后再试")

    # 稳定列序：先按首行键，后续行多出的键追加在末尾
    fieldnames: List[str] = list(records[0].keys())
    for rec in records[1:]:
        for k in rec.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    with open(process_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})

    return os.path.abspath(process_path)


def format_response(resp_text: str, method_name: str, module_name: str, usage: dict = None) -> str:
    # 保存usage
    usage = usage or {}
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%H%M%S")
    usage_path = os.path.join(usage_dir, f"{today}.json")
    if usage:
        if os.path.exists(usage_path):
            with open(usage_path, "r", encoding="utf-8") as f:
                _usage = json.load(f)
            if now in usage:
                now_usage = add_usages([usage, _usage[now]])
            else:
                now_usage = usage
            _usage.update({now: now_usage})
        else:
            _usage = {now: usage}
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(_usage, f, ensure_ascii=False)

    # 保存结果
    if GTS_SAVE_FILE in [True, 'true', '1', 'True']:
        process_dir = os.path.join(gangtise_workspace_path, method_name)
        if not os.path.exists(process_dir):
            os.makedirs(process_dir, exist_ok=True)
        extension = 'json'
        process_path = os.path.join(process_dir, f"{module_name}_{today}_{now}.{extension}")
        with open(process_path, "w", encoding="utf-8") as f:
            f.write(resp_text)
        resp_text += f"\n\n工具调用结果已保存到文件：\n`{os.path.abspath(process_path)}`\n\n"

    return resp_text


OPENAPI_SKILL_VERSION = "1.6.7"
SKILL_CHECK_URL = "https://open.gangtise.com/application/skills-backend/version?skill=openapi"


def check_version(large_version: bool = True):
    response = requests.get(SKILL_CHECK_URL)
    if response.status_code == 200 and large_version:
        return response.json()["state"] == "success" and response.json()["version"].split(".")[0] == \
            OPENAPI_SKILL_VERSION.split(".")[0] and response.json()["version"].split(".")[1] == \
            OPENAPI_SKILL_VERSION.split(".")[1]
    elif response.status_code == 200 and not large_version:
        return response.json()["state"] == "success" and response.json()["version"] == OPENAPI_SKILL_VERSION
    else:
        return False


if __name__ == "__main__":
    print("检查 gangtise-file 相关配置")
    if not GTS_AUTHORIZATION:
        print("  无法检测到gangtise密钥环境变量或授权文件, gangtise-agent 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-agent 可以正常工作")
    if GTS_SAVE_FILE is None:
        print("  环境变量 GTS_SAVE_FILE 未配置, 默认值为 False, gangtise服务端 将不保存查询结果到文件中")
    elif GTS_SAVE_FILE == "True":
        print("  环境变量 GTS_SAVE_FILE 为 True, gangtise服务端 将保存查询结果到文件中")
    else:
        print("  环境变量 GTS_SAVE_FILE 为 False, gangtise服务端 将不保存查询结果到文件中")
    if check_version(large_version=False):
        print("  gangtise-file 版本为最新")
    else:
        print("  gangtise-file 版本不是最新, 建议进行更新")
    print(f"  gangtise-file 工作文件目录: {gangtise_workspace_path}")