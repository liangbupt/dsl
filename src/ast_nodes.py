"""
AST节点定义模块

定义了DSL抽象语法树的所有节点类型，用于表示客服机器人脚本的结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class NodeType(Enum):
    """节点类型枚举"""
    BOT = "bot"
    INTENT = "intent"
    STATE = "state"
    VARIABLE = "variable"
    FUNCTION = "function"
    ACTION = "action"
    TRANSITION = "transition"
    EXPRESSION = "expression"
    CONDITION = "condition"


@dataclass
class ASTNode:
    """AST节点基类"""
    node_type: NodeType = field(default=NodeType.EXPRESSION)
    line: int = 0
    column: int = 0


@dataclass
class Expression(ASTNode):
    """表达式节点基类"""
    node_type: NodeType = field(default=NodeType.EXPRESSION)


@dataclass
class StringLiteral(Expression):
    """字符串字面量"""
    value: str = ""
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class NumberLiteral(Expression):
    """数字字面量"""
    value: Union[int, float] = 0
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class BooleanLiteral(Expression):
    """布尔字面量"""
    value: bool = False
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class ListLiteral(Expression):
    """列表字面量"""
    elements: List[Expression] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class Identifier(Expression):
    """标识符"""
    name: str = ""
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class BinaryOp(Expression):
    """二元运算表达式"""
    operator: str = ""  # +, -, *, /, ==, !=, <, >, <=, >=, and, or
    left: Expression = None
    right: Expression = None
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class UnaryOp(Expression):
    """一元运算表达式"""
    operator: str = ""  # not, -
    operand: Expression = None
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class FunctionCall(Expression):
    """函数调用表达式"""
    name: str = ""
    arguments: List[Expression] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class MemberAccess(Expression):
    """成员访问表达式"""
    object: Expression = None
    member: str = ""
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


@dataclass
class IndexAccess(Expression):
    """索引访问表达式"""
    object: Expression = None
    index: Expression = None
    node_type: NodeType = field(default=NodeType.EXPRESSION, init=False)


# ============ 语句节点 ============

@dataclass
class Statement(ASTNode):
    """语句节点基类"""
    node_type: NodeType = field(default=NodeType.ACTION)


@dataclass
class SayStatement(Statement):
    """say语句 - 机器人说话"""
    message: Expression = None
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class AskStatement(Statement):
    """ask语句 - 向用户提问并存储回答"""
    prompt: Expression = None
    variable: str = ""
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class SetStatement(Statement):
    """set语句 - 设置变量"""
    variable: str = ""
    value: Expression = None
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class GotoStatement(Statement):
    """goto语句 - 跳转到状态"""
    state_name: str = ""
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class CallStatement(Statement):
    """call语句 - 调用函数"""
    function_call: FunctionCall = None
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class ReturnStatement(Statement):
    """return语句"""
    value: Optional[Expression] = None
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class IfStatement(Statement):
    """if语句"""
    condition: Expression = None
    then_block: List[Statement] = field(default_factory=list)
    elif_blocks: List[tuple] = field(default_factory=list)  # List of (condition, statements)
    else_block: Optional[List[Statement]] = None
    node_type: NodeType = field(default=NodeType.CONDITION, init=False)


@dataclass
class WhileStatement(Statement):
    """while语句"""
    condition: Expression = None
    body: List[Statement] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class ForStatement(Statement):
    """for语句"""
    variable: str = ""
    iterable: Expression = None
    body: List[Statement] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class ExpressionStatement(Statement):
    """表达式语句"""
    expression: Expression = None
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


# ============ 定义节点 ============

@dataclass
class IntentDef(ASTNode):
    """意图定义"""
    name: str = ""
    patterns: List[str] = field(default_factory=list)  # 关键词模式
    description: str = ""  # 意图描述，用于LLM理解
    examples: List[str] = field(default_factory=list)  # 示例句子
    node_type: NodeType = field(default=NodeType.INTENT, init=False)


@dataclass
class TransitionRule(ASTNode):
    """状态转换规则"""
    intent_name: str = ""  # 触发意图
    target_state: str = ""  # 目标状态
    condition: Optional[Expression] = None  # 可选条件
    node_type: NodeType = field(default=NodeType.TRANSITION, init=False)


@dataclass
class FallbackHandler(ASTNode):
    """兜底处理器"""
    statements: List[Statement] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class EventHandler(ASTNode):
    """事件处理器"""
    event_type: str = ""  # on_enter, on_exit, on_message
    statements: List[Statement] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.ACTION, init=False)


@dataclass
class StateDef(ASTNode):
    """状态定义"""
    name: str = ""
    is_initial: bool = False
    is_final: bool = False
    handlers: List[EventHandler] = field(default_factory=list)
    transitions: List[TransitionRule] = field(default_factory=list)
    fallback: Optional[FallbackHandler] = None
    node_type: NodeType = field(default=NodeType.STATE, init=False)


@dataclass
class VariableDef(ASTNode):
    """变量定义"""
    name: str = ""
    initial_value: Optional[Expression] = None
    var_type: Optional[str] = None  # 可选类型注解
    node_type: NodeType = field(default=NodeType.VARIABLE, init=False)


@dataclass
class ParameterDef:
    """函数参数定义"""
    name: str = ""
    default_value: Optional[Expression] = None
    param_type: Optional[str] = None


@dataclass
class FunctionDef(ASTNode):
    """函数定义"""
    name: str = ""
    parameters: List[ParameterDef] = field(default_factory=list)
    body: List[Statement] = field(default_factory=list)
    return_type: Optional[str] = None
    node_type: NodeType = field(default=NodeType.FUNCTION, init=False)


@dataclass
class BotDef(ASTNode):
    """机器人定义 - 顶层节点"""
    name: str = ""
    description: str = ""
    intents: List[IntentDef] = field(default_factory=list)
    states: List[StateDef] = field(default_factory=list)
    variables: List[VariableDef] = field(default_factory=list)
    functions: List[FunctionDef] = field(default_factory=list)
    initial_state: Optional[str] = None
    node_type: NodeType = field(default=NodeType.BOT, init=False)


@dataclass
class Program(ASTNode):
    """程序节点 - 最顶层"""
    bots: List[BotDef] = field(default_factory=list)
    node_type: NodeType = field(default=NodeType.BOT, init=False)


# ============ 辅助函数 ============

def pretty_print(node: ASTNode, indent: int = 0) -> str:
    """格式化打印AST节点"""
    prefix = "  " * indent
    result = []
    
    if isinstance(node, Program):
        result.append(f"{prefix}Program:")
        for bot in node.bots:
            result.append(pretty_print(bot, indent + 1))
    
    elif isinstance(node, BotDef):
        result.append(f"{prefix}Bot: {node.name}")
        if node.intents:
            result.append(f"{prefix}  Intents:")
            for intent in node.intents:
                result.append(pretty_print(intent, indent + 2))
        if node.states:
            result.append(f"{prefix}  States:")
            for state in node.states:
                result.append(pretty_print(state, indent + 2))
        if node.variables:
            result.append(f"{prefix}  Variables:")
            for var in node.variables:
                result.append(pretty_print(var, indent + 2))
        if node.functions:
            result.append(f"{prefix}  Functions:")
            for func in node.functions:
                result.append(pretty_print(func, indent + 2))
    
    elif isinstance(node, IntentDef):
        result.append(f"{prefix}Intent: {node.name}")
        result.append(f"{prefix}  patterns: {node.patterns}")
        if node.description:
            result.append(f"{prefix}  description: {node.description}")
    
    elif isinstance(node, StateDef):
        flags = []
        if node.is_initial:
            flags.append("initial")
        if node.is_final:
            flags.append("final")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        result.append(f"{prefix}State: {node.name}{flag_str}")
        for handler in node.handlers:
            result.append(f"{prefix}  {handler.event_type}:")
            for stmt in handler.statements:
                result.append(pretty_print(stmt, indent + 2))
        for trans in node.transitions:
            cond = f" if {trans.condition}" if trans.condition else ""
            result.append(f"{prefix}  when {trans.intent_name} -> {trans.target_state}{cond}")
    
    elif isinstance(node, VariableDef):
        val = f" = {node.initial_value}" if node.initial_value else ""
        result.append(f"{prefix}var {node.name}{val}")
    
    elif isinstance(node, FunctionDef):
        params = ", ".join(p.name for p in node.parameters)
        result.append(f"{prefix}func {node.name}({params})")
    
    elif isinstance(node, SayStatement):
        result.append(f"{prefix}say {node.message}")
    
    elif isinstance(node, AskStatement):
        result.append(f"{prefix}ask {node.prompt} -> {node.variable}")
    
    elif isinstance(node, SetStatement):
        result.append(f"{prefix}set {node.variable} = {node.value}")
    
    elif isinstance(node, GotoStatement):
        result.append(f"{prefix}goto {node.state_name}")
    
    elif isinstance(node, IfStatement):
        result.append(f"{prefix}if {node.condition}")
    
    else:
        result.append(f"{prefix}{type(node).__name__}: {node}")
    
    return "\n".join(result)
