# 自然语言到SQL智能查询系统（MCP-MySQL）

## 项目简介

本项目基于MCP（Model Context Protocol）协议，结合大语言模型（LLM）和MySQL数据库，实现了**自然语言到SQL的智能查询系统**。
用户可通过命令行或现代化Web界面（Streamlit GUI），用中文自然语言描述查询需求，系统自动生成高效、安全的SQL并返回结果。
项目支持多轮对话、Few-shot示例增强、SQL优化建议、查询日志、表结构浏览等丰富功能，适合教学、数据分析、智能BI等场景。

---

## 评分任务与功能实现

### 基础任务
| 子任务             | 要求说明                                                         | 实现情况 |
|--------------------|------------------------------------------------------------------|----------|
| MCP 服务运行       | 下载并部署 alexcc4/mcp-mysql-server，连接 MySQL 实例              | ✅        |
| 通义 API 调用模块  | 输入自然语言 → 输出 SQL；支持基础 prompt 构造                     | ✅        |
| 查询控制模块       | 获取 schema，执行 SQL，解析并返回 JSON 结果                      | ✅        |
| CLI 界面实现       | 可在终端交互输入自然语言并返回查询结果                            | ✅        |

### MCP功能增强任务
| 功能项             | 实现说明                                                         | 实现情况 |
|--------------------|------------------------------------------------------------------|----------|
| 查询日志记录 /logs | MCP Server 记录每次执行的 SQL 和时间戳                            | ✅        |
| 查询结果分页       | 长查询结果支持用户在 CLI 输入 next 或自动分页返回                 | ✅        |
| 表结构简化输出     | /schema 支持按表名过滤返回 schema                                 | ✅        |

### MCP安全控制任务
| 安全项             | 实现说明                                                         | 实现情况 |
|--------------------|------------------------------------------------------------------|----------|
| 只读 SQL 白名单过滤| MCP 内部解析 SQL，仅允许 SELECT 语句                             | ✅        |
| 关键字段访问控制   | 禁止查询包含 password、salary 等字段                             | ✅        |
| 简易 SQL 注入防御机制| 拦截明显拼接注入或关键词注入的攻击行为                        | ✅        |

### 大模型优化任务/UI扩展任务
| 优化项             | 实现说明                                                         | 实现情况 |
|--------------------|------------------------------------------------------------------|----------|
| Prompt 模板优化    | 提高生成 SQL 的准确率（准确性提升 ≥10% 可得满分）                | ✅        |
| 多轮提示结构 / Few-shot | 在 prompt 中引入示例对 / 对话上下文优化                     | ✅        |
| SQL 执行计划简化建议| 提示模型生成更高效的 SQL 查询结构（如避免子查询嵌套）           | ✅        |
| GUI 界面（如 Streamlit）| 可输入自然语言，展示生成 SQL 和查询结果表格                | ✅        |

---

## 目录结构

```
mcp-mysql-server/
├── cli.py                # 命令行交互入口
├── gui.py                # Streamlit前端主程序
├── run_gui.py            # 启动GUI的脚本
├── llm_client.py         # LLM API交互与Prompt工程
├── mcp_client.py         # MCP客户端，负责与后端通信
├── main.py               # FastAPI后端服务（MCP Server）
├── query.log             # 查询日志
└── pyproject.toml        # 依赖管理
 
...
```

---

## 快速开始

### 1. 安装依赖


```bash
pip install streamlit pandas requests fastapi uvicorn
```

### 2. 配置数据库和API密钥

- 配置MySQL数据库（main.py）：
  ```
  "host": os.getenv("DB_HOST", "localhost"),
  "user": os.getenv("DB_USER", "root"),
  "passwd": os.getenv("DB_PASSWORD", "password"),
  "db": os.getenv("DB_NAME", "college"),
  "port": int(os.getenv("DB_PORT", 3306))
  ```
- 配置大模型API密钥及URL（llm_client.py）：
  ```
  QWEN_API_KEY=sk-xxxxxx
  QWEN_API_URL
  ```

### 3. 启动后端服务

```bash
python main.py
# 默认监听 http://localhost:8000
```

### 4. GUI模式

```bash
python run_gui.py
# 浏览器访问 http://localhost:8501
```

### 5. 命令行模式

```bash
python main.py cli
```

---

## 主要界面功能（GUI）

- **自然语言查询**：输入需求，自动生成SQL并分页显示结果。
- **数据库表结构**：可视化查看所有表及字段、主外键、示例数据。
- **表列表**：一览所有表及字段数，支持快速跳转表结构。
- **JSON结果查询**：直接获取结构化JSON结果。
- **查询日志**：历史查询一键回溯。

## Reference
https://github.com/alexcc4/mcp-mysql-server/tree/master