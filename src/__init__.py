"""
智能客服机器人 DSL 解释器

这是一个用于描述智能客服机器人应答逻辑的领域特定语言(DSL)及其解释器。
"""

__version__ = '1.0.0'
__author__ = 'DSL Project'

from .ast_nodes import (
    Program, BotDef, IntentDef, StateDef, VariableDef, FunctionDef,
    Statement, Expression
)
from .lexer import BotLexer, tokenize
from .parser import BotParser, parse
from .interpreter import Interpreter, IOHandler, Environment
from .llm_client import LLMClient, create_llm_client, IntentInfo, IntentResult

__all__ = [
    # AST节点
    'Program', 'BotDef', 'IntentDef', 'StateDef', 'VariableDef', 'FunctionDef',
    'Statement', 'Expression',
    
    # 词法分析
    'BotLexer', 'tokenize',
    
    # 语法分析
    'BotParser', 'parse',
    
    # 解释器
    'Interpreter', 'IOHandler', 'Environment',
    
    # LLM客户端
    'LLMClient', 'create_llm_client', 'IntentInfo', 'IntentResult',
]
