import requests
import json
import os
from typing import Dict, Any
from mcp_client import get_sample_rows

# 通义千问API配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "sk-1b77e5585d7247a1959baa1d8249264f")
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def generate_sql_from_prompt(prompt: str, schema: Dict[str, Any]) -> str:
    #根据自然语言提示和数据库模式生成SQL
    # 构造包含数据库Schema的Prompt
    schema_description = "数据库模式信息：\n"

    valid_tables = 0
    for table_name, columns in schema.items():
        # 跳过无效的表结构
        if not isinstance(columns, list) or not columns:
            print(f"警告：表 {table_name} 的列信息无效")
            continue

        if not isinstance(columns[0], dict):
            print(f"警告：表 {table_name} 的列格式不正确")
            continue

        schema_description += f"表名: {table_name}\n"
        schema_description += "  列信息:\n"

        for column in columns:
            col_name = column.get("Field") or column.get("name", "未知列名")
            col_type = column.get("Type") or column.get("type", "未知类型")
            col_null = column.get("Null") or column.get("null", "未知")

            schema_description += f"    {col_name}: {col_type} ({'可空' if col_null == 'YES' else '非空'})\n"

        # 新增：附加样例数据
        try:
            samples = get_sample_rows(table_name, 3)
            if samples:
                schema_description += "  示例数据:\n"
                for row in samples:
                    row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
                    schema_description += f"    {row_str}\n"
        except Exception as e:
            schema_description += "  （获取示例数据失败）\n"

        valid_tables += 1

    if valid_tables == 0:
        print("错误：未找到有效的表结构信息")
        return "错误：无法获取数据库表结构"

    # 构造完整Prompt
    full_prompt = f"""
    请根据以下数据库模式和用户查询生成正确的SQL语句。
    只返回SQL语句，不要任何解释。

    {schema_description}

    用户查询: {prompt}
    SQL语句:
    """

    # 调用通义API
    response = call_qwen_api(full_prompt)
    return parse_sql_response(response)


def call_qwen_api(prompt: str) -> Dict[str, Any]:
    """调用通义千问API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}"
    }

    payload = {
        "model": "qwen-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "parameters": {
            "temperature": 0.1,
            "max_tokens": 200
        }
    }

    try:
        print(f"发送请求到API: {QWEN_API_URL}")
        response = requests.post(QWEN_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        print(f"API返回状态码: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求错误: {e}")
        print(f"响应内容: {response.text if 'response' in locals() else '无'}")
        return {"error": f"API请求失败: {str(e)}"}
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"响应内容: {response.text[:500] if 'response' in locals() else '无'}")
        return {"error": f"JSON解析失败: {str(e)}"}
    except Exception as e:
        print(f"未知错误: {e}")
        return {"error": f"未知错误: {str(e)}"}


def parse_sql_response(response: Dict[str, Any]) -> str:
    """解析API返回的SQL结果"""
    if "error" in response:
        return f"错误: {response['error']}"

    try:
        # 适配通义千问API返回格式
        output = response.get("output", {})
        text = output.get("text", "")

        if not text:
            # 尝试从其他可能的字段获取内容
            choices = response.get("choices", [{}])
            message = choices[0].get("message", {})
            text = message.get("content", "")

            if not text:
                # 打印完整响应用于调试
                print(f"完整API响应: {json.dumps(response, indent=2)}")
                return "错误: API未返回有效内容"

        # 清理SQL语句
        sql = text.strip()

        # 移除可能包含的引号
        if sql.startswith(('"', "'")) and sql.endswith(('"', "'")):
            sql = sql[1:-1].strip()

        return sql
    except Exception as e:
        print(f"解析响应错误: {e}")
        return f"解析错误: {str(e)}"