import MySQLdb
import os
from typing import Dict, Any, List

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "passwd": os.getenv("DB_PASSWORD", "SYX040304"),
    "db": os.getenv("DB_NAME", "college"),
    "port": int(os.getenv("DB_PORT", 3306))
}


def get_connection():
    """获取数据库连接"""
    try:
        return MySQLdb.connect(**DB_CONFIG)
    except MySQLdb.Error as e:
        print(f"数据库连接错误: {e}")
        raise


def get_schema() -> Dict[str, Any]:
    """获取数据库表结构信息"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        # 获取所有表名
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        # 提取表名（适配不同MySQL版本）
        table_names = []
        for table in tables:
            table_name = next(iter(table.values()))
            table_names.append(table_name)

        # 获取每个表的结构
        schema = {}
        for table_name in table_names:
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()

            # 确保列信息是列表
            if isinstance(columns, tuple):
                columns = list(columns)

            schema[table_name] = columns

        return schema
    finally:
        if cursor:
            cursor.close()
        conn.close()


def query_data(sql: str) -> Dict[str, Any]:
    """执行SQL查询并返回结果"""
    if not is_safe_query(sql):
        return {
            "success": False,
            "error": "检测到潜在不安全查询。仅允许SELECT查询。"
        }

    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        # 设置为只读事务
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("START TRANSACTION")

        try:
            #执行成功返回
            cursor.execute(sql)
            results = cursor.fetchall()
            conn.commit()

            return {
                "success": True,
                "results": results,
                "rowCount": len(results)
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    finally:
        if cursor:
            cursor.close()
        conn.close()


def is_safe_query(sql: str) -> bool:
    """检查查询是否安全（只允许SELECT）"""
    sql_lower = sql.lower().strip()
    unsafe_keywords = [
        "insert", "update", "delete", "drop", "alter",
        "truncate", "create", "grant", "revoke"
    ]

    # 检查是否以SELECT开头且不包含危险关键字
    return sql_lower.startswith("select") and not any(
        keyword in sql_lower for keyword in unsafe_keywords
    )


def get_sample_rows(table_name: str, n: int = 3) -> list:
    """获取指定表的前n行数据"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {n}")
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        conn.close()