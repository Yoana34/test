import requests
import os
import re
from typing import Dict, Any, List

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")


def get_schema() -> Dict[str, Any]:
    """通过MCP Server获取数据库表结构信息"""
    resp = requests.get(f"{MCP_SERVER_URL}/schema")
    resp.raise_for_status()
    data = resp.json()
    # 兼容原有格式
    if "tables" in data:
        return data["tables"]
    return data


def query_data(sql: str) -> Dict[str, Any]:
    """通过MCP Server执行SQL查询并返回结果"""
    resp = requests.post(f"{MCP_SERVER_URL}/query_data", json={"sql": sql})
    resp.raise_for_status()
    return resp.json()


def get_sample_rows(table_name: str, n: int = 3) -> list:
    """通过MCP Server获取指定表的前n行数据"""
    resp = requests.get(f"{MCP_SERVER_URL}/sample_rows", params={"table": table_name, "n": n})
    resp.raise_for_status()
    return resp.json().get("rows", [])


def get_logs(log_file: str = "query.log", limit: int = 100) -> list:
    """通过MCP Server获取最近的SQL查询日志，智能拼接多行SQL"""
    # 优先尝试API
    try:
        resp = requests.get(f"{MCP_SERVER_URL}/logs", params={"limit": limit, "raw": 1})
        resp.raise_for_status()
        raw_lines = resp.json().get("raw_lines")
        if raw_lines:
            return _parse_logs(raw_lines)[-limit:]
        # 否则回退到logs字段
        logs = resp.json().get("logs", [])
        if logs:
            return logs[-limit:]
    except Exception:
        pass
    # 兼容本地文件读取（如直读本地日志）
    if not os.path.exists(log_file):
        return []
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return _parse_logs(lines)[-limit:]

def _parse_logs(log_lines):
    logs = []
    current = None
    for line in log_lines:
        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - SQL: ', line):
            if current:
                logs.append(current)
            ts, sql = line.strip().split(' - SQL: ', 1)
            current = {"timestamp": ts, "sql": sql}
        elif current:
            current["sql"] += "\n" + line.strip()
    if current:
        logs.append(current)
    return logs