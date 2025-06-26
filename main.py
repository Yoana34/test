import os
import logging
from typing import Any, Dict
import MySQLdb
from fastapi import FastAPI
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
def api_get_logs(limit: int = 100):
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
    if not is_safe_query(sql):
        return {"success": False, "error": "Potentially unsafe query detected. Only SELECT queries are allowed."}
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