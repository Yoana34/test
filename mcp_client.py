import requests
import os
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
    """通过MCP Server获取最近的SQL查询日志"""
    resp = requests.get(f"{MCP_SERVER_URL}/logs", params={"limit": limit})
    resp.raise_for_status()
    return resp.json().get("logs", [])