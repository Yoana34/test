import os
import logging
from typing import Any, Dict
import MySQLdb
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
from datetime import datetime

# Create MCP server instance
mcp = FastMCP("mysql-server")

# Database connection configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "passwd": os.getenv("DB_PASSWORD", "SYX040304"),
    "db": os.getenv("DB_NAME", "college"),
    "port": int(os.getenv("DB_PORT", 3306))
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mysql-mcp-server")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FORBIDDEN_FIELDS = ['password', 'salary', 'ssn', 'credit_card']

def security_check(sql: str) -> (bool, str):
    """安全控制判断总函数."""
    is_readonly, reason = is_readonly_query(sql)
    if not is_readonly:
        return False, reason

    has_forbidden, reason = contains_forbidden_fields(sql)
    if has_forbidden:
        return False, reason

    is_injection, reason = is_injection_attempt(sql)
    if is_injection:
        return False, reason

    return True, ""

def is_readonly_query(sql: str) -> (bool, str):
    """检测是否是仅select语句"""
    sql_strip_lower = sql.strip().lower()
    if not sql_strip_lower.startswith('select'):
        return False, "Security violation: Only SELECT statements are allowed."
    
    if ';' in sql_strip_lower.rstrip(';'):
        return False, "Security violation: Multiple SQL statements are not allowed."
    
    unsafe_keywords = ["insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", "revoke"]
    for keyword in unsafe_keywords:
        if re.search(r'\b' + keyword + r'\b', sql_strip_lower):
            return False, f"Security violation: Use of '{keyword}' is not allowed in SELECT statements."
    return True, ""

def contains_forbidden_fields(sql: str) -> (bool, str):
    """查询是否访问敏感字段（支持表名、别名、引号等写法）"""
    sql_lower = sql.lower()
    # 只检测select ... from之间的内容
    m = re.search(r'select(.*?)from', sql_lower, re.DOTALL)
    if not m:
        return False, ""
    select_fields = m.group(1)
    for field in FORBIDDEN_FIELDS:
        # 匹配 salary, t.salary, instructor.salary, `salary`, "salary"
        pattern = r'(\b|\W)(' + re.escape(field) + r')(\b|\W)'
        if re.search(pattern, select_fields):
            return True, f"Security violation: Access to sensitive field '{field}' is forbidden."
    return False, ""

def is_injection_attempt(sql: str) -> (bool, str):
    """拦截SQL注入攻击"""
    sql_lower = sql.lower()
    injection_patterns = [
        r"(\s*or\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(\s*union\s+select\s+)",
        r"(--|#|/\*)"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, sql_lower):
            return True, "Security violation: Potential SQL injection pattern detected."

    suspicious_keywords = ['sleep', 'benchmark', 'load_file', 'outfile', 'information_schema']
    for keyword in suspicious_keywords:
        if keyword in sql_lower:
            return True, f"Security violation: Use of suspicious keyword '{keyword}' is not allowed."
            
    return False, ""

class QueryRequest(BaseModel):
    sql: str

@app.get("/schema")
def api_get_schema():
    return get_schema()

@app.get("/tables")
def api_get_tables():
    return get_tables()

@app.post("/query_data")
def api_query_data(req: QueryRequest):
    return query_data(req.sql)

@app.get("/logs")
def api_get_logs(request: Request, limit: int = 100):
    if request.query_params.get("raw") == "1":
        if not os.path.exists("query.log"):
            return {"raw_lines": []}
        with open("query.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
        return {"raw_lines": lines}

    # Fallback for simple clients
    logs = []
    if not os.path.exists("query.log"):
        return {"logs": []}
    with open("query.log", "r", encoding="utf-8") as f:
        for line in f:
            if " - SQL: " in line:
                ts, sql = line.strip().split(" - SQL: ", 1)
                logs.append({"timestamp": ts, "sql": sql})
    return {"logs": logs[-limit:]}

@app.get("/sample_rows")
def api_sample_rows(table: str, n: int = 3):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(f"SELECT * FROM `{table}` LIMIT {n}")
        rows = cursor.fetchall()
        return {"rows": rows}
    except Exception as e:
        return {"rows": [], "error": str(e)}
    finally:
        if cursor:
            cursor.close()
        conn.close()

# 保持原有MCP server功能
@mcp.resource("mysql://schema")
def get_schema() -> Dict[str, Any]:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [list(table.values())[0] for table in tables]
        schema = {}
        for table_name in table_names:
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            table_schema = []
            for column in columns:
                table_schema.append({
                    "name": column["Field"],
                    "type": column["Type"],
                    "null": column["Null"],
                    "key": column["Key"],
                    "default": column["Default"],
                    "extra": column["Extra"]
                })
            schema[table_name] = table_schema
        return {"database": DB_CONFIG["db"], "tables": schema}
    finally:
        if cursor:
            cursor.close()
        conn.close()

@mcp.resource("mysql://tables")
def get_tables() -> Dict[str, Any]:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [list(table.values())[0] for table in tables]
        return {"database": DB_CONFIG["db"], "tables": table_names}
    except MySQLdb.Error as e:
        print(f"Database connection error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        conn.close()

def get_connection():
    try:
        return MySQLdb.connect(**DB_CONFIG)
    except MySQLdb.Error as e:
        print(f"Database connection error: {e}")
        raise

def is_safe_query(sql: str) -> bool:
    sql_lower = sql.lower()
    unsafe_keywords = ["insert", "update", "delete", "drop", "alter", "truncate", "create"]
    return not any(keyword in sql_lower for keyword in unsafe_keywords)

@mcp.tool()
def query_data(sql: str) -> Dict[str, Any]:
    is_safe, reason = security_check(sql)
    if not is_safe:
        logger.warning(f"Blocked unsafe query: {sql}. Reason: {reason}")
        return {"success": False, "error": reason}
        
    logger.info(f"Executing query: {sql}")
    with open("query.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - SQL: {sql}\n")
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("START TRANSACTION")
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            conn.commit()
            return {"success": True, "results": results, "rowCount": len(results)}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
    finally:
        if cursor:
            cursor.close()
        conn.close()

def validate_config():
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}")
        logger.warning("Using default values, which may not work in production.")

def main():
    validate_config()
    print(f"MySQL MCP server started, connected to {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        from cli import run_cli
        from llm_client import generate_sql_from_prompt
        from mcp_client import get_schema, query_data, get_logs
        print("进入命令行自然语言查询模式")
        run_cli(get_schema, query_data, generate_sql_from_prompt, get_logs)
    else:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)