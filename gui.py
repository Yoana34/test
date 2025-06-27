import streamlit as st
import pandas as pd
import json
from typing import Dict, Any
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_client import generate_sql_from_prompt
from mcp_client import get_schema, query_data, get_logs, get_tables

# 页面配置
st.set_page_config(
    page_title="自然语言数据库查询系统",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 1rem;
        margin-top: 0;
    }
    .sql-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
    }
    .result-box {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #ffe6e6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    .json-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #6c757d;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
    }
    .table-info {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    /* 缩小header字体 */
    h1 {
        font-size: 1.8rem !important;
    }
    
    /* 缩小subheader字体 */
    h2 {
        font-size: 1.4rem !important;
    }
    
    h3 {
        font-size: 1.2rem !important;
    }
    
    /* 缩小侧边栏标题字体 */
    .sidebar h1, .sidebar h2, .sidebar h3 {
        font-size: 1.2rem !important;
    }
    
    /* 减少页面顶部空白 */
    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 减少主内容区域的顶部间距 */
    .main > div {
        padding-top: 0 !important;
    }
    
    /* 减少Streamlit默认的顶部间距 */
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp > header + div {
        padding-top: 0 !important;
    }
    
    /* 减少页面整体的顶部间距 */
    .stApp {
        padding-top: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

def check_database_connection():
    """检查数据库连接状态"""
    try:
        schema = get_schema()
        return True, schema
    except Exception as e:
        return False, str(e)

def natural_language_query_page():
    """自然语言查询页面"""
    st.header("🔍 自然语言查询")
    
    # 检查数据库连接
    connected, schema_or_error = check_database_connection()
    if not connected:
        st.error(f"❌ 数据库连接失败: {schema_or_error}")
        return
    
    # 输入区域
    col1, col2 = st.columns([3, 1])
    
    with col1:
        natural_query = st.text_area(
            "请输入您的查询需求:",
            value=st.session_state.get('natural_query', ''),
            height=120,
            placeholder="例如：列出所有学生的姓名和年龄"
        )
        
        # 查询按钮
        if st.button("生成并执行查询", type="primary", use_container_width=True):
            if natural_query.strip():
                process_query(natural_query.strip())
            else:
                st.warning("请输入查询内容")
    
    with col2:
        st.subheader("📝 示例查询")
        examples = [
            "查询所有课程的名称和学分",
            "找出所有有多个先修课程的课程",
            "查询所有有多个导师的学生姓名",
            "查找课程'International Finance'的先修课程标题",
            "统计每个学生的选课数量"
        ]
        
        for example in examples:
            if st.button(example, key=f"example_{example}"):
                st.session_state.natural_query = example
                st.rerun()

def database_schema_page():
    """数据库表结构页面"""
    st.header("📋 数据库表结构")
    
    # 检查数据库连接
    connected, schema_or_error = check_database_connection()
    if not connected:
        st.error(f"❌ 数据库连接失败: {schema_or_error}")
        return
    
    schema = schema_or_error
    
    # 表选择器
    table_names = list(schema.keys())
    # 如果从表列表页面选择了表，则默认选择该表
    default_index = 0
    if 'selected_table' in st.session_state and st.session_state.selected_table in table_names:
        default_index = table_names.index(st.session_state.selected_table) + 1  # +1 因为第一个是"全部表"
    
    selected_table = st.selectbox("选择要查看的表:", ["全部表"] + table_names, index=default_index)
    
    if selected_table == "全部表":
        # 显示所有表的结构
        for table_name, table_info in schema.items():
            with st.expander(f"{table_name}", expanded=True):
                st.write(f"**表名:** {table_name}")
                st.write(f"**字段数量:** {len(table_info)}")
                st.write("**字段详情:**")
                
                # 创建字段信息表格 - 处理列表格式的字段信息
                field_data = []
                for field_info in table_info:
                    field_data.append({
                        "字段名": field_info.get("name", "未知"),
                        "类型": field_info.get("type", "未知"),
                        "可空": "是" if field_info.get("null", "YES") == "YES" else "否",
                        "键": field_info.get("key", ""),
                        "默认值": field_info.get("default", "无") if field_info.get("default") is not None else "无",
                        "额外": field_info.get("extra", "")
                    })
                
                df = pd.DataFrame(field_data)
                st.dataframe(df, use_container_width=True)
    else:
        # 显示选中表的结构
        table_info = schema[selected_table]
        st.write(f"**表名:** {selected_table}")
        st.write(f"**字段数量:** {len(table_info)}")
        st.write("**字段详情:**")
        
        # 创建字段信息表格 - 处理列表格式的字段信息
        field_data = []
        for field_info in table_info:
            field_data.append({
                "字段名": field_info.get("name", "未知"),
                "类型": field_info.get("type", "未知"),
                "可空": "是" if field_info.get("null", "YES") == "YES" else "否",
                "键": field_info.get("key", ""),
                "默认值": field_info.get("default", "无") if field_info.get("default") is not None else "无",
                "额外": field_info.get("extra", "")
            })
        
        df = pd.DataFrame(field_data)
        st.dataframe(df, use_container_width=True)
        
        # 清除session state中的选择
        if 'selected_table' in st.session_state:
            del st.session_state.selected_table

def table_list_page():
    """表列表页面"""
    st.header("📋 数据库表列表")
    
    # 检查数据库连接
    connected, schema_or_error = check_database_connection()
    if not connected:
        st.error(f"❌ 数据库连接失败: {schema_or_error}")
        return
    
    schema = schema_or_error
    
    # 获取表列表
    try:
        tables = get_tables()
    except Exception as e:
        st.error(f"❌ 获取表列表失败: {str(e)}")
        return
    
    # 显示表列表
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("所有表")
        
        # 创建表信息表格
        table_data = []
        for table_name in tables:
            # 正确处理列表格式的字段信息
            field_count = len(schema.get(table_name, []))
            table_data.append({
                "表名": table_name,
                "字段数": field_count,
                "状态": "✅ 正常"
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
    
    with col2:
        st.subheader("快速操作")
        
        # 快速查看表结构
        if tables:
            selected_table = st.selectbox("选择表查看结构:", tables)
            if st.button("查看表结构"):
                # 设置session state来触发页面跳转
                st.session_state.selected_table = selected_table
                st.session_state.switch_to_schema = True
                st.rerun()
        else:
            st.info("📭 没有可用的表")

def json_query_page():
    """JSON结果查询页面"""
    st.header("🔍 自然语言查询 (JSON结果)")
    
    # 检查数据库连接
    connected, schema_or_error = check_database_connection()
    if not connected:
        st.error(f"❌ 数据库连接失败: {schema_or_error}")
        return
    
    # 输入区域
    natural_query = st.text_area(
        "请输入您的查询需求:",
        value=st.session_state.get('json_query', ''),
        height=120,
        placeholder="例如：列出所有学生的姓名和年龄"
    )
    
    # 查询按钮
    if st.button("生成SQL并获取JSON结果", type="primary", use_container_width=True):
        if natural_query.strip():
            process_json_query(natural_query.strip())
        else:
            st.warning("请输入查询内容")

def query_logs_page():
    """查询日志页面"""
    st.header("📝 查询日志")
    
    # 日志设置
    col1, col2 = st.columns([2, 1])
    
    with col1:
        log_limit = st.slider("显示日志条数:", min_value=10, max_value=200, value=50, step=10)
    
    with col2:
        if st.button("刷新日志", type="primary"):
            st.rerun()
    
    # 获取日志
    try:
        logs = get_logs(limit=log_limit)
        
        if not logs:
            st.info("暂无查询日志")
            return
        
        # 显示日志
        st.subheader(f"📋 最近 {len(logs)} 条查询日志")
        
        for i, log in enumerate(reversed(logs)):
            with st.expander(f"查询 {len(logs) - i} - {log.get('timestamp', '未知时间')}", expanded=False):
                st.markdown(f'<div class="sql-box">{log.get("sql", "无SQL内容")}</div>', unsafe_allow_html=True)
                
                # 显示时间戳
                if log.get('timestamp'):
                    st.caption(f"执行时间: {log['timestamp']}")
    
    except Exception as e:
        st.error(f"❌ 获取日志失败: {str(e)}")

def process_query(natural_query: str):
    """处理自然语言查询"""
    # 初始化计数器
    if 'query_count' not in st.session_state:
        st.session_state.query_count = 0
    if 'success_count' not in st.session_state:
        st.session_state.success_count = 0
    
    st.session_state.query_count += 1
    
    # 显示查询进度
    with st.spinner("正在生成SQL..."):
        try:
            # 获取数据库结构
            schema = get_schema()
            if not schema:
                st.error("❌ 无法获取数据库结构")
                return
            
            # 生成SQL
            generated_sql = generate_sql_from_prompt(natural_query, schema)
            
            if "错误" in generated_sql:
                st.error(f"❌ SQL生成失败: {generated_sql}")
                return
            
            # 显示生成的SQL
            st.subheader("📝 生成的SQL语句")
            st.markdown(f'<div class="sql-box">{generated_sql}</div>', unsafe_allow_html=True)
            
            # 执行查询
            with st.spinner("正在执行查询..."):
                result = query_data(generated_sql)
                
                if result["success"]:
                    st.session_state.success_count += 1
                    
                    # 显示查询结果
                    st.subheader("📊 查询结果")
                    
                    if result["rowCount"] == 0:
                        st.info("没有找到匹配的数据")
                    else:
                        # 转换为DataFrame并显示
                        df = pd.DataFrame(result["results"])
                        st.dataframe(df, use_container_width=True)
                        
                        # 显示统计信息
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("返回行数", result["rowCount"])
                        with col2:
                            st.metric("列数", len(df.columns))
                        with col3:
                            st.metric("查询状态", "✅ 成功")
                        
                        # 提供下载功能
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"query_result_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                        # 显示结果统计
                        st.markdown('<div class="result-box">✅ 查询执行成功！</div>', unsafe_allow_html=True)
                else:
                    st.error(f"❌ 查询执行失败: {result['error']}")
                    st.markdown(f'<div class="error-box">❌ 查询执行失败: {result["error"]}</div>', unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"❌ 处理查询时发生错误: {str(e)}")
            st.markdown(f'<div class="error-box">❌ 系统错误: {str(e)}</div>', unsafe_allow_html=True)

def process_json_query(natural_query: str):
    """处理JSON结果查询"""
    with st.spinner("正在生成SQL..."):
        try:
            # 获取数据库结构
            schema = get_schema()
            if not schema:
                st.error("❌ 无法获取数据库结构")
                return
            
            # 生成SQL
            generated_sql = generate_sql_from_prompt(natural_query, schema)
            
            if "错误" in generated_sql:
                st.error(f"❌ SQL生成失败: {generated_sql}")
                return
            
            # 显示生成的SQL
            st.subheader("📝 生成的SQL语句")
            st.markdown(f'<div class="sql-box">{generated_sql}</div>', unsafe_allow_html=True)
            
            # 执行查询
            with st.spinner("正在执行查询..."):
                result = query_data(generated_sql)
                
                if result["success"]:
                    # 显示JSON结果
                    st.subheader("📊 JSON查询结果")
                    
                    # 格式化JSON
                    json_result = {
                        "query": natural_query,
                        "generated_sql": generated_sql,
                        "success": True,
                        "row_count": result["rowCount"],
                        "column_count": len(result["results"][0]) if result["results"] else 0,
                        "data": result["results"]
                    }
                    
                    # 显示格式化的JSON
                    st.markdown(f'<div class="json-box">{json.dumps(json_result, indent=2, ensure_ascii=False)}</div>', unsafe_allow_html=True)
                    
                    # 提供JSON下载
                    json_str = json.dumps(json_result, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="下载JSON文件",
                        data=json_str,
                        file_name=f"query_result_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                    
                    # 同时显示表格形式
                    if result["rowCount"] > 0:
                        st.subheader("📊 表格形式结果")
                        df = pd.DataFrame(result["results"])
                        st.dataframe(df, use_container_width=True)
                    
                    st.markdown('<div class="result-box">✅ JSON查询执行成功！</div>', unsafe_allow_html=True)
                else:
                    error_result = {
                        "query": natural_query,
                        "generated_sql": generated_sql,
                        "success": False,
                        "error": result["error"]
                    }
                    st.markdown(f'<div class="json-box">{json.dumps(error_result, indent=2, ensure_ascii=False)}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="error-box">❌ 查询执行失败: {result["error"]}</div>', unsafe_allow_html=True)
                    
        except Exception as e:
            error_result = {
                "query": natural_query,
                "success": False,
                "error": str(e)
            }
            st.markdown(f'<div class="json-box">{json.dumps(error_result, indent=2, ensure_ascii=False)}</div>', unsafe_allow_html=True)
            st.error(f"❌ 处理查询时发生错误: {str(e)}")

def main():
    # 主标题
    st.markdown('<h1 class="main-header">自然语言数据库查询系统</h1>', unsafe_allow_html=True)
    
    # 侧边栏 - 数据库连接状态
    with st.sidebar:
        st.header("📊 系统状态")
        
        # 显示数据库连接状态
        connected, schema_or_error = check_database_connection()
        if connected:
            st.success("✅ 数据库连接正常")
            st.write(f"📋 数据库表数量: {len(schema_or_error)}")
        else:
            st.error("❌ 数据库连接失败")
            st.write(f"错误: {schema_or_error}")
        
        st.divider()
        
        # 导航菜单
        st.header("🧭 功能导航")
        
        # 检查是否需要跳转到表结构页面
        if st.session_state.get('switch_to_schema', False):
            current_page = "数据库表结构"
            # 清除跳转标志
            st.session_state.switch_to_schema = False
        else:
            current_page = st.session_state.get('current_page', "自然语言查询")
        
        page = st.selectbox(
            "选择功能:",
            [
                "自然语言查询",
                "数据库表结构", 
                "表列表",
                "JSON结果查询",
                "查询日志"
            ],
            index=["自然语言查询", "数据库表结构", "表列表", "JSON结果查询", "查询日志"].index(current_page)
        )
        
        # 更新当前页面状态
        st.session_state.current_page = page
        
        st.divider()
        
        # 使用说明
        st.subheader("💡 使用说明")
        st.markdown("""
        **自然语言查询**: 输入自然语言，自动生成SQL并显示结果
        
        **数据库表结构**: 查看所有表的详细字段信息
        
        **表列表**: 查看所有表的概览信息
        
        **JSON结果查询**: 输入自然语言，获取JSON格式的查询结果
        
        **查询日志**: 查看历史查询记录
        """)
    
    # 根据选择显示对应页面
    if page == "自然语言查询":
        natural_language_query_page()
    elif page == "数据库表结构":
        database_schema_page()
    elif page == "表列表":
        table_list_page()
    elif page == "JSON结果查询":
        json_query_page()
    elif page == "查询日志":
        query_logs_page()

if __name__ == "__main__":
    main()