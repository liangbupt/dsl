# 智能客服机器人 DSL 解释器

## 项目概述

本项目实现了一个用于描述智能客服机器人应答逻辑的领域特定语言（DSL）及其解释器。该DSL基于状态机模型，可以定义客服机器人在不同业务场景下的对话流程，并通过集成大语言模型（LLM）API实现用户意图识别。

## 功能特性

- 🎯 **自定义DSL语法**：专门用于描述客服机器人对话逻辑，支持中文标识符
- 🤖 **LLM意图识别**：调用OpenAI API进行用户意图识别，支持降级到本地规则匹配
- 📝 **多业务场景支持**：提供电商、银行、电信三个业务场景脚本范例
- 🔄 **状态机驱动**：基于状态转换的对话流程管理
- 💻 **命令行界面**：简洁的CLI交互方式，支持调试模式
- ✅ **完整测试覆盖**：30个单元测试全部通过

## DSL语法概览

```
# 定义一个客服机器人
bot "电商客服" {
    # 定义意图
    intent 查询订单 {
        patterns: ["订单", "物流", "快递", "发货"]
        description: "用户想要查询订单状态"
        examples: ["我的订单到哪了", "查一下物流"]
    }
    
    # 定义状态
    state 初始状态 initial {
        on_enter {
            say "您好，欢迎使用智能客服！"
        }
        
        when 查询订单 -> 订单查询状态
        when 退货退款 -> 退款处理状态
        
        fallback {
            say "抱歉，我没有理解您的意思，请重新描述"
        }
    }
    
    state 结束状态 final {
        on_enter {
            say "感谢使用，再见！"
        }
    }
    
    # 定义变量
    var order_id = ""
    var user_name = ""
    
    # 定义函数
    func validate_order(id) {
        if length(id) >= 10 {
            return true
        }
        return false
    }
}
```

## 项目结构

```
dsl/
├── src/
│   ├── __init__.py       # 模块初始化
│   ├── ast_nodes.py      # AST节点定义
│   ├── lexer.py          # 词法分析器 (PLY)
│   ├── parser.py         # 语法分析器 (PLY)
│   ├── interpreter.py    # 解释器核心
│   ├── llm_client.py     # LLM API客户端
│   └── cli.py            # 命令行界面
├── scripts/
│   ├── ecommerce.bot     # 电商客服脚本
│   ├── banking.bot       # 银行客服脚本
│   └── telecom.bot       # 电信客服脚本
├── tests/
│   ├── test_parser.py    # 解析器测试
│   └── test_interpreter.py # 解释器测试
├── docs/
│   ├── grammar.md        # DSL语法规范文档
│   └── development.md    # 开发文档
├── requirements.txt
├── .gitignore
└── README.md
```

## 安装与运行

### 环境要求

- Python 3.8+
- PLY (Python Lex-Yacc)
- OpenAI Python SDK
- colorama（可选，用于彩色输出）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行客服机器人

```bash
# 运行电商客服脚本（使用模拟LLM，无需API密钥）
python src/cli.py scripts/ecommerce.bot

# 运行银行客服脚本
python src/cli.py scripts/banking.bot

# 运行电信客服脚本
python src/cli.py scripts/telecom.bot

# 启用调试模式
python src/cli.py scripts/ecommerce.bot --debug

# 查看帮助
python src/cli.py --help
```

### 使用 DeepSeek API（推荐）

```bash
# 配置 DeepSeek API密钥
# Windows
set DEEPSEEK_API_KEY=your_api_key_here

# Linux/Mac
export DEEPSEEK_API_KEY=your_api_key_here

# 使用 DeepSeek V3 进行意图识别（默认）
python src/cli.py scripts/ecommerce.bot --llm

# 或显式指定
python src/cli.py scripts/ecommerce.bot --llm --provider deepseek
```

### 使用 OpenAI API（可选）

```bash
# 配置 OpenAI API密钥
# Windows
set OPENAI_API_KEY=your_api_key_here

# Linux/Mac
export OPENAI_API_KEY=your_api_key_here

# 使用 OpenAI 进行意图识别
python src/cli.py scripts/ecommerce.bot --llm --provider openai
```

## 业务场景示例

| 脚本 | 场景 | 主要功能 |
|------|------|----------|
| `ecommerce.bot` | 电商客服 | 订单查询、退货退款、商品咨询、投诉建议 |
| `banking.bot` | 银行客服 | 账户查询、转账汇款、信用卡服务、贷款咨询、挂失冻结 |
| `telecom.bot` | 电信客服 | 话费查询、套餐办理、故障报修、宽带服务、充值缴费 |

## 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行解析器测试
python -m pytest tests/test_parser.py -v

# 运行解释器测试
python -m pytest tests/test_interpreter.py -v
```

## 文档

- [DSL语法规范](docs/grammar.md) - 完整的语法说明和示例
- [开发文档](docs/development.md) - 架构设计和扩展指南

## 技术栈

- **编程语言**: Python 3.8+
- **词法/语法分析**: PLY (Python Lex-Yacc)
- **LLM集成**: DeepSeek API（默认）、OpenAI API（兼容）
- **版本管理**: Git

## 许可证

MIT License
