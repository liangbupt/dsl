# 开发文档

## 1. 项目概述

本项目实现了一个用于描述智能客服机器人应答逻辑的领域特定语言（DSL）及其解释器。该DSL基于状态机模型，通过集成大语言模型（LLM）API实现用户意图识别。

### 1.1 技术栈

- **编程语言**: Python 3.8+
- **词法/语法分析**: PLY (Python Lex-Yacc)
- **LLM集成**: OpenAI API
- **版本管理**: Git

### 1.2 项目结构

```
dsl/
├── src/
│   ├── __init__.py       # 模块初始化
│   ├── ast_nodes.py      # AST节点定义
│   ├── lexer.py          # 词法分析器
│   ├── parser.py         # 语法分析器
│   ├── interpreter.py    # 解释器
│   ├── llm_client.py     # LLM客户端
│   └── cli.py            # 命令行界面
├── scripts/
│   ├── ecommerce.bot     # 电商客服脚本
│   ├── banking.bot       # 银行客服脚本
│   └── telecom.bot       # 电信客服脚本
├── tests/
│   ├── test_parser.py    # 解析器测试
│   └── test_interpreter.py # 解释器测试
├── docs/
│   ├── grammar.md        # 语法文档
│   └── development.md    # 开发文档
├── requirements.txt
└── README.md
```

## 2. 模块设计

### 2.1 AST节点模块 (ast_nodes.py)

定义了抽象语法树的所有节点类型。

#### 主要类

| 类名 | 描述 |
|------|------|
| `Program` | 程序顶层节点，包含多个机器人定义 |
| `BotDef` | 机器人定义，包含意图、状态、变量、函数 |
| `IntentDef` | 意图定义 |
| `StateDef` | 状态定义 |
| `VariableDef` | 变量定义 |
| `FunctionDef` | 函数定义 |
| `Expression` | 表达式基类 |
| `Statement` | 语句基类 |

#### 设计决策

- 使用 `dataclass` 简化节点定义
- 每个节点包含行号信息用于错误报告
- 表达式和语句使用继承体系便于扩展

### 2.2 词法分析器模块 (lexer.py)

使用PLY实现词法分析，将源代码转换为Token序列。

#### Token类型

- **关键字**: `bot`, `intent`, `state`, `var`, `func`, `say`, `ask`, `set`, `goto`, `if`, `else`, `while`, `for`, `return`, 等
- **运算符**: `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `>`, `->`, 等
- **字面量**: 字符串、数字、布尔值
- **标识符**: 支持中文标识符

#### 特点

- 支持中文标识符和关键字混用
- 支持单行注释 (`#`)
- 字符串支持转义字符

### 2.3 语法分析器模块 (parser.py)

使用PLY实现语法分析，生成AST。

#### BNF语法（简化）

```
program     ::= bot_list
bot_list    ::= bot_def | bot_list bot_def
bot_def     ::= 'bot' STRING '{' bot_body '}'
bot_body    ::= (intent_def | state_def | variable_def | function_def)*

intent_def  ::= 'intent' IDENTIFIER '{' intent_attrs '}'
state_def   ::= 'state' IDENTIFIER modifiers '{' state_body '}'
variable_def::= 'var' IDENTIFIER ['=' expression]
function_def::= 'func' IDENTIFIER '(' params ')' '{' statements '}'

statement   ::= say_stmt | ask_stmt | set_stmt | goto_stmt | if_stmt | ...
expression  ::= or_expr
or_expr     ::= and_expr | or_expr 'or' and_expr
...
```

#### 优先级处理

使用PLY的优先级声明处理运算符优先级，避免冲突。

### 2.4 解释器模块 (interpreter.py)

执行AST，驱动对话流程。

#### 核心类

| 类名 | 描述 |
|------|------|
| `Environment` | 变量环境，支持嵌套作用域 |
| `IOHandler` | I/O处理器，抽象输入输出 |
| `Interpreter` | 解释器主类 |

#### 执行流程

```
1. load_program() - 加载程序
2. start() - 启动机器人，执行初始状态的on_enter
3. process_input() - 处理用户输入
   a. 意图识别
   b. 匹配转换规则
   c. 执行转换或fallback
4. 循环直到结束状态
```

#### 内置函数

解释器提供丰富的内置函数：
- 字符串处理: `length`, `upper`, `lower`, `trim`, `contains`, 等
- 类型转换: `str`, `int`, `float`, `bool`
- 列表操作: `first`, `last`, `append`, `pop`, `slice`
- 数学函数: `abs`, `min`, `max`, `round`

### 2.5 LLM客户端模块 (llm_client.py)

集成大语言模型进行意图识别。

#### 类

| 类名 | 描述 |
|------|------|
| `LLMClient` | OpenAI API客户端 |
| `MockLLMClient` | 模拟客户端，用于测试 |
| `IntentInfo` | 意图信息数据类 |
| `IntentResult` | 识别结果数据类 |

#### 意图识别流程

```
1. 构建意图描述（patterns, description, examples）
2. 构建上下文（当前状态、变量）
3. 调用LLM API进行意图识别
4. 解析响应，提取意图和实体
5. 如果API失败，降级到本地规则匹配
```

#### Prompt设计

```
系统提示词：
你是一个智能客服意图识别助手。你的任务是分析用户输入，识别其意图。
返回JSON格式结果：
{
    "intent": "意图名称",
    "confidence": 0.95,
    "entities": {"实体名": "实体值"},
    "reasoning": "简短的推理说明"
}
```

### 2.6 CLI模块 (cli.py)

提供命令行交互界面。

#### 功能

- 加载和执行DSL脚本
- 交互式对话
- 调试命令：显示状态、变量
- 脚本热重载

## 3. LLM使用说明

### 3.1 API配置

设置环境变量：

```bash
# Windows
set OPENAI_API_KEY=your_api_key_here
set OPENAI_BASE_URL=https://api.openai.com/v1  # 可选

# Linux/Mac
export OPENAI_API_KEY=your_api_key_here
```

### 3.2 运行模式

```bash
# 使用模拟LLM（默认，不需要API）
python src/cli.py scripts/ecommerce.bot

# 使用真实LLM API
python src/cli.py scripts/ecommerce.bot --llm
```

### 3.3 兼容的API服务

支持OpenAI兼容的API服务：
- OpenAI官方API
- Azure OpenAI
- 其他兼容服务（通过设置OPENAI_BASE_URL）

## 4. 扩展指南

### 4.1 添加新的内置函数

在 `interpreter.py` 的 `_create_builtins()` 方法中添加：

```python
self.builtins['new_function'] = lambda x: x.do_something()
```

### 4.2 添加新的语句类型

1. 在 `ast_nodes.py` 中定义新的语句类
2. 在 `lexer.py` 中添加相关Token
3. 在 `parser.py` 中添加语法规则
4. 在 `interpreter.py` 中添加执行逻辑

### 4.3 自定义LLM客户端

继承 `LLMClient` 类并实现 `recognize_intent` 方法：

```python
class CustomLLMClient(LLMClient):
    def recognize_intent(self, user_input, intents, context):
        # 自定义实现
        pass
```

## 5. 测试

### 5.1 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_parser.py -v
python -m pytest tests/test_interpreter.py -v

# 或使用unittest
python -m unittest discover tests -v
```

### 5.2 测试覆盖

- 词法分析：关键字、运算符、字面量、中文支持
- 语法分析：各种语法结构的正确解析
- 解释执行：语句执行、表达式求值、状态转换
- LLM集成：意图识别、降级处理

## 6. 已知限制

1. 不支持类和对象（面向过程设计）
2. 不支持异常处理（try-catch）
3. 不支持模块导入（单文件脚本）
4. LLM API调用可能有延迟

## 7. 未来改进

- [ ] 添加调试器支持
- [ ] 支持脚本模块化
- [ ] 添加可视化状态机编辑器
- [ ] 支持更多LLM服务商
- [ ] 添加对话历史记录
- [ ] 支持多轮上下文理解

## 8. 版本历史

### v1.0.0 (2024-11-28)

- 初始版本
- 完整的DSL语法支持
- 状态机对话管理
- OpenAI API意图识别
- 三个业务场景示例
