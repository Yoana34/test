import os
import time
from typing import Dict, Any, Callable
import re


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_menu():
    """显示主菜单"""
    clear_screen()
    print("=" * 80)
    print("  基于大模型的自然语言数据库查询系统  ".center(50))
    print("=" * 80)
    print("\n功能:")
    print("1. 输入自然语言查询")
    print("2. 查看数据库表结构")
    print("3. 查看表列表")
    print("4. 输入自然语言查询并输出JSON结果")
    print("5. 查看查询日志")
    print("0. 退出系统")
    print("=" * 80)


def get_user_choice():
    """获取用户选择"""
    try:
        choice = input("\n请输入选项(0-5): ")
        return int(choice)
    except ValueError:
        return -1


def run_cli(
        get_schema_func: Callable[[], Dict[str, Any]],
        query_data_func: Callable[[str], Dict[str, Any]],
        generate_sql_func: Callable[[str, Dict[str, Any]], str],
        get_logs_func: Callable[[], Any] = None
):
    """运行CLI界面"""
    while True:
        display_menu()
        choice = get_user_choice()

        if choice == 1:
            run_query_mode(get_schema_func, query_data_func, generate_sql_func)
        elif choice == 2:
            display_schema(get_schema_func)
        elif choice == 3:
            display_tables(get_schema_func)
        elif choice == 4:
            run_query_mode_json(get_schema_func, query_data_func, generate_sql_func)
        elif choice == 5:
            if get_logs_func:
                display_logs(get_logs_func)
            else:
                print("日志功能未实现！")
                time.sleep(1)
        elif choice == 0:
            print("感谢使用，再见！")
            break
        else:
            print("无效选项，请重新输入！")
            time.sleep(1)


def run_query_mode(
        get_schema_func: Callable[[], Dict[str, Any]],
        query_data_func: Callable[[str], Dict[str, Any]],
        generate_sql_func: Callable[[str, Dict[str, Any]], str]
):
    """运行查询模式"""
    clear_screen()
    print("=" * 80)
    print("  自然语言查询模式  ".center(50))
    print("=" * 80)
    print("\n请输入自然语言查询，例如：'列出所有学生的姓名和年龄'")
    print("输入'返回'回到主菜单\n")

    query = input("自然语言查询: ")
    if query.lower() == "返回":
        return

    process_query(query, get_schema_func, query_data_func, generate_sql_func)


def process_query(
        query: str,
        get_schema_func: Callable[[], Dict[str, Any]],
        query_data_func: Callable[[str], Dict[str, Any]],
        generate_sql_func: Callable[[str, Dict[str, Any]], str]
):
    """处理用户查询"""
    print("\n正在生成SQL...")
    schema = get_schema_func()
    sql = generate_sql_func(query, schema)

    if "错误" in sql:
        print(f"SQL生成错误: {sql}")
        input("\n按Enter键继续...")
        return

    print(f"生成的SQL: {sql}\n")
    print("正在执行查询...")

    result = query_data_func(sql)

    if not result["success"]:
        print(f"查询执行错误: {result['error']}")
        # 自动提示表结构字段
        if "Unknown column" in result["error"]:
            table = None
            # 尝试从SQL中提取表名
            m = re.search(r"from [`']?(\w+)[`']?", sql, re.IGNORECASE)
            if m:
                table = m.group(1)
            if table:
                schema = get_schema_func()
                if table in schema:
                    print(f"表 {table} 字段如下：")
                    for col in schema[table]:
                        print("  - ", col.get('Field') or col.get('name', '未知列名'))
        input("\n按Enter键继续...")
        return

    display_query_results(result)


def display_query_results(result: Dict[str, Any]):
    """显示查询结果（分页，严格等宽表格，支持中英文对齐）"""
    import re
    def visual_len(s):
        return sum(2 if re.match(r'[\u4e00-\u9fff]', c) else 1 for c in str(s))
    def pad(s, width):
        s = str(s)
        pad_len = width - visual_len(s)
        return s + ' ' * pad_len

    print("=" * 80)
    print("  查询结果  ".center(50))
    print("=" * 80)

    if result["rowCount"] == 0:
        print("没有找到匹配的结果。")
        input("\n按Enter键继续...")
        return
    columns = list(result["results"][0].keys())
    col_widths = [visual_len(col) for col in columns]
    for row in result["results"]:
        for i, col in enumerate(columns):
            col_widths[i] = max(col_widths[i], visual_len(row.get(col, "")))
    header = "| " + " | ".join(pad(col, col_widths[i]) for i, col in enumerate(columns)) + " |"
    sep = "|" + "-".join("-" * (w + 2) for w in col_widths) + "|"
    page_size = 10
    total = result["rowCount"]
    rows = result["results"]
    page = 0
    while True:
        start = page * page_size
        end = min(start + page_size, total)
        print(header)
        print(sep)
        for row in rows[start:end]:
            row_str = "| " + " | ".join(pad(row.get(col, ""), col_widths[i]) for i, col in enumerate(columns)) + " |"
            print(row_str)
        print(f"\n第 {page+1} 页，共 {((total-1)//page_size)+1} 页。显示 {start+1}-{end} 行，共 {total} 行。")
        if end >= total:
            print("\n" + "=" * 80)
            input("已到末页，按Enter键继续...")
            break
        cmd = input("输入 next 查看下一页，或其他键返回: ").strip().lower()
        if cmd == "next":
            page += 1
            clear_screen()
            print("=" * 80)
            print("  查询结果  ".center(50))
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            break


def display_schema(get_schema_func: Callable[[], Dict[str, Any]]):
    """显示数据库表结构，支持按表名过滤"""
    clear_screen()
    print("=" * 80)
    print("  数据库表结构  ".center(50))
    print("=" * 80)

    schema = get_schema_func()
    if not schema:
        print("没有找到表结构信息。")
        input("\n按Enter键继续...")
        return

    table_name = input("输入表名可只看该表结构，直接回车显示全部: ").strip()
    tables = [table_name] if table_name and table_name in schema else schema.keys()
    if table_name and table_name not in schema:
        print(f"未找到表 {table_name}，显示全部表结构。\n")
        tables = schema.keys()

    for tname in tables:
        columns = schema[tname]
        print(f"表名: {tname}")
        print("  列信息:")
        if not isinstance(columns, list) or not columns:
            print("    列信息不可用")
            continue
        for col in columns:
            col_name = col.get("Field") or col.get("name", "未知列名")
            col_type = col.get("Type") or col.get("type", "未知类型")
            col_null = col.get("Null") or col.get("null", "未知")
            col_key = col.get("Key") or col.get("key", "")
            print(f"    {col_name} - {col_type} "
                  f"({'可空' if col_null == 'YES' else '非空'}) "
                  f"({'' if not col_key else '主键' if col_key == 'PRI' else '索引'})")
        print()
    input("\n按Enter键继续...")


def display_tables(get_schema_func: Callable[[], Dict[str, Any]]):
    """显示所有表名"""
    clear_screen()
    print("=" * 80)
    print("  数据库表列表  ".center(50))
    print("=" * 80)

    schema = get_schema_func()
    if not schema:
        print("没有找到表结构信息。")
        input("\n按Enter键继续...")
        return

    print("表名列表：")
    for table_name in schema.keys():
        print("  -", table_name)

    input("\n按Enter键继续...")


def display_logs(get_logs_func: Callable[[], Any]):
    """显示查询日志"""
    clear_screen()
    print("=" * 80)
    print("  查询日志  ".center(50))
    print("=" * 80)
    logs = get_logs_func()
    if not logs:
        print("没有日志记录。")
        input("\n按Enter键继续...")
        return
    for log in logs:
        print(f"[{log.get('timestamp', '')}] {log.get('sql', '')}")
    input("\n按Enter键继续...")


def run_query_mode_json(
        get_schema_func: Callable[[], Dict[str, Any]],
        query_data_func: Callable[[str], Dict[str, Any]],
        generate_sql_func: Callable[[str, Dict[str, Any]], str]
):
    """运行查询模式（输出JSON）"""
    clear_screen()
    print("=" * 80)
    print("  自然语言查询模式（JSON输出）  ".center(50))
    print("=" * 80)
    print("\n请输入自然语言查询，例如：'列出所有学生的姓名和年龄'")
    print("输入'返回'回到主菜单\n")

    query = input("自然语言查询: ")
    if query.lower() == "返回":
        return

    process_query_json(query, get_schema_func, query_data_func, generate_sql_func)


def process_query_json(
        query: str,
        get_schema_func: Callable[[], Dict[str, Any]],
        query_data_func: Callable[[str], Dict[str, Any]],
        generate_sql_func: Callable[[str, Dict[str, Any]], str]
):
    """处理用户查询并输出JSON"""
    import json
    print("\n正在生成SQL...")
    schema = get_schema_func()
    sql = generate_sql_func(query, schema)

    if "错误" in sql:
        print(f"SQL生成错误: {sql}")
        input("\n按Enter键继续...")
        return

    print(f"生成的SQL: {sql}\n")
    print("正在执行查询...")

    result = query_data_func(sql)

    if not result["success"]:
        print(f"查询执行错误: {result['error']}")
        # 自动提示表结构字段
        if "Unknown column" in result["error"]:
            table = None
            m = re.search(r"from [`']?(\w+)[`']?", sql, re.IGNORECASE)
            if m:
                table = m.group(1)
            if table:
                schema = get_schema_func()
                if table in schema:
                    print(f"表 {table} 字段如下：")
                    for col in schema[table]:
                        print("  - ", col.get('Field') or col.get('name', '未知列名'))
        input("\n按Enter键继续...")
        return

    print("\nJSON结果如下：")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    input("\n按Enter键继续...")


if __name__ == "__main__":
    from llm_client import generate_sql_from_prompt
    from mcp_client import get_schema, query_data

    print("欢迎使用自然语言数据库查询 CLI！")
    run_cli(get_schema, query_data, generate_sql_from_prompt)