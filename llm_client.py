import requests
import json
import os
from typing import Dict, Any
from mcp_client import get_sample_rows

# 通义千问API配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "sk-1b77e5585d7247a1959baa1d8249264f")
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def generate_sql_from_prompt(prompt: str, schema: Dict[str, Any], history: list = None) -> str:
    """
    根据自然语言提示和数据库模式生成高效、准确的SQL。
    支持few-shot示例和上下文。
    """
    # 1. 构造数据库Schema描述
    schema_description = "数据库结构如下：\n"
    for table_name, columns in schema.items():
        if not isinstance(columns, list) or not columns:
            continue
        schema_description += f"表: {table_name}\n  字段: "
        schema_description += ", ".join(
            f"{col.get('Field') or col.get('name', '未知')}: {col.get('Type') or col.get('type', '未知')}" for col in columns
        ) + "\n"
        # 主键/外键/约束
        pk = [col.get('Field') or col.get('name') for col in columns if (col.get('Key') or col.get('key')) == 'PRI']
        if pk:
            schema_description += f"  主键: {', '.join(pk)}\n"
        fk = [col.get('Field') or col.get('name') for col in columns if (col.get('Key') or col.get('key')) == 'MUL']
        if fk:
            schema_description += f"  外键: {', '.join(fk)}\n"
        # 示例数据
        try:
            samples = get_sample_rows(table_name, 2)
            if samples:
                schema_description += "  示例: " + "; ".join(
                    ", ".join(f"{k}:{v}" for k, v in row.items()) for row in samples
                ) + "\n"
        except Exception:
            pass
    
    # 2. Few-shot示例（可扩展）
    few_shot_examples = [
        {
            "user": "列出所有学生的姓名和年龄",
            "sql": "SELECT name, age FROM student;"
        },
        {
            "user": "查询所有课程的名称和学分",
            "sql": "SELECT name, credit FROM course;"
        },
        {
            "user": "找出所有有多个先修课程的课程",
            "sql": "SELECT course_id FROM prerequisite GROUP BY course_id HAVING COUNT(*) > 1;"
        },
        {
            "user": "查询所有有多个导师的学生姓名",
            "sql": "SELECT s.name FROM student s JOIN advisor a ON s.id = a.s_id GROUP BY s.id HAVING COUNT(a.t_id) > 1;"
        },
        {
            "user": "查找课程'International Finance'的先修课程标题",
            "sql": "SELECT c2.title FROM course c1 JOIN prerequisite p ON c1.id = p.course_id JOIN course c2 ON p.prereq_id = c2.id WHERE c1.title = 'International Finance';"
        }
    ]
    
    # 3. 多轮上下文（如有）
    context_str = ""
    if history:
        for turn in history[-3:]:  # 只取最近3轮
            context_str += f"用户: {turn['user']}\nSQL: {turn['sql']}\n"
    
    # 4. SQL优化指令
    optimize_tip = (
        "请生成高效、可读性强的SQL，避免不必要的嵌套和低效子查询。"
        "如可用JOIN替代子查询请优先使用JOIN。"
        "如可用聚合函数请直接使用。"
        "如有更优写法请直接优化。"
        "只输出最终SQL，不要解释。"
    )
    
    # 5. 组装Prompt
    prompt_parts = [
        "你是一个专业的SQL生成助手。",
        schema_description,
        "--- 示例 ---"
    ]
    for ex in few_shot_examples:
        prompt_parts.append(f"用户: {ex['user']}\nSQL: {ex['sql']}")
    if context_str:
        prompt_parts.append("--- 上下文 ---\n" + context_str)
    prompt_parts.append("--- 任务 ---")
    prompt_parts.append(f"用户: {prompt}")
    prompt_parts.append(optimize_tip)
    prompt_parts.append("SQL:")
    full_prompt = "\n".join(prompt_parts)
    
    # 调用API
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