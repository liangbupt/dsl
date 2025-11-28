"""
解释器模块

执行DSL抽象语法树，驱动客服机器人的对话逻辑。
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

from .ast_nodes import (
    Program, BotDef, IntentDef, StateDef, VariableDef, FunctionDef,
    EventHandler, TransitionRule, FallbackHandler,
    Statement, SayStatement, AskStatement, SetStatement, GotoStatement,
    CallStatement, ReturnStatement, IfStatement, WhileStatement, ForStatement,
    ExpressionStatement,
    Expression, StringLiteral, NumberLiteral, BooleanLiteral, ListLiteral,
    Identifier, BinaryOp, UnaryOp, FunctionCall, MemberAccess, IndexAccess
)
from .llm_client import LLMClient, IntentInfo, IntentResult, create_llm_client


class ExecutionState(Enum):
    """执行状态"""
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    FINISHED = "finished"
    ERROR = "error"


class ReturnException(Exception):
    """用于函数返回的异常"""
    def __init__(self, value=None):
        self.value = value


class GotoException(Exception):
    """用于状态跳转的异常"""
    def __init__(self, state_name: str):
        self.state_name = state_name


@dataclass
class Environment:
    """执行环境，存储变量和函数"""
    variables: Dict[str, Any] = field(default_factory=dict)
    functions: Dict[str, FunctionDef] = field(default_factory=dict)
    parent: Optional['Environment'] = None
    
    def get(self, name: str) -> Any:
        """获取变量值"""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"未定义的变量: {name}")
    
    def set(self, name: str, value: Any):
        """设置变量值"""
        # 如果变量已在当前或父作用域存在，更新它
        if name in self.variables:
            self.variables[name] = value
        elif self.parent and self._exists_in_parent(name):
            self.parent.set(name, value)
        else:
            # 新变量在当前作用域创建
            self.variables[name] = value
    
    def _exists_in_parent(self, name: str) -> bool:
        """检查变量是否在父作用域存在"""
        if self.parent is None:
            return False
        if name in self.parent.variables:
            return True
        return self.parent._exists_in_parent(name)
    
    def define(self, name: str, value: Any):
        """在当前作用域定义新变量"""
        self.variables[name] = value
    
    def get_function(self, name: str) -> Optional[FunctionDef]:
        """获取函数定义"""
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name)
        return None


@dataclass
class IOHandler:
    """I/O处理器接口"""
    output_callback: Callable[[str], None] = print
    input_callback: Callable[[str], str] = input
    
    def say(self, message: str):
        """输出消息"""
        self.output_callback(message)
    
    def ask(self, prompt: str) -> str:
        """询问用户并获取输入"""
        return self.input_callback(prompt)


class Interpreter:
    """DSL解释器"""
    
    def __init__(
        self,
        io_handler: Optional[IOHandler] = None,
        llm_client: Optional[LLMClient] = None
    ):
        """
        初始化解释器
        
        Args:
            io_handler: I/O处理器
            llm_client: LLM客户端
        """
        self.io = io_handler or IOHandler()
        self.llm = llm_client or create_llm_client(use_mock=True)
        
        # 当前执行的机器人
        self.current_bot: Optional[BotDef] = None
        
        # 执行环境
        self.env: Optional[Environment] = None
        
        # 状态机相关
        self.current_state: Optional[StateDef] = None
        self.states: Dict[str, StateDef] = {}
        self.intents: Dict[str, IntentDef] = {}
        
        # 执行状态
        self.execution_state = ExecutionState.RUNNING
        
        # 内置函数
        self.builtins = self._create_builtins()
    
    def _create_builtins(self) -> Dict[str, Callable]:
        """创建内置函数"""
        return {
            # 字符串函数
            'length': lambda x: len(x) if x else 0,
            'upper': lambda s: s.upper() if isinstance(s, str) else s,
            'lower': lambda s: s.lower() if isinstance(s, str) else s,
            'trim': lambda s: s.strip() if isinstance(s, str) else s,
            'contains': lambda s, sub: sub in s if isinstance(s, str) else False,
            'startswith': lambda s, pre: s.startswith(pre) if isinstance(s, str) else False,
            'endswith': lambda s, suf: s.endswith(suf) if isinstance(s, str) else False,
            'replace': lambda s, old, new: s.replace(old, new) if isinstance(s, str) else s,
            'split': lambda s, sep=' ': s.split(sep) if isinstance(s, str) else [],
            'join': lambda lst, sep='': sep.join(str(x) for x in lst) if isinstance(lst, list) else '',
            
            # 类型转换
            'str': lambda x: str(x),
            'int': lambda x: int(x) if x else 0,
            'float': lambda x: float(x) if x else 0.0,
            'bool': lambda x: bool(x),
            
            # 列表函数
            'append': self._builtin_append,
            'pop': lambda lst: lst.pop() if lst else None,
            'first': lambda lst: lst[0] if lst else None,
            'last': lambda lst: lst[-1] if lst else None,
            'slice': lambda lst, start, end=None: lst[start:end],
            
            # 数学函数
            'abs': abs,
            'min': min,
            'max': max,
            'round': round,
            
            # 实用函数
            'print': lambda *args: self.io.say(' '.join(str(a) for a in args)),
            'format': lambda template, *args: template.format(*args),
            'match': lambda pattern, s: bool(re.match(pattern, s)) if isinstance(s, str) else False,
            
            # 状态相关
            'current_state': lambda: self.current_state.name if self.current_state else None,
        }
    
    def _builtin_append(self, lst: list, item) -> list:
        """列表追加函数"""
        if isinstance(lst, list):
            lst.append(item)
        return lst
    
    def load_program(self, program: Program):
        """加载程序"""
        if not program.bots:
            raise RuntimeError("程序中没有定义机器人")
        
        # 默认加载第一个机器人
        self.load_bot(program.bots[0])
    
    def load_bot(self, bot: BotDef):
        """加载机器人定义"""
        self.current_bot = bot
        
        # 初始化环境
        self.env = Environment()
        
        # 注册意图
        self.intents = {intent.name: intent for intent in bot.intents}
        
        # 注册状态
        self.states = {state.name: state for state in bot.states}
        
        # 注册函数
        for func in bot.functions:
            self.env.functions[func.name] = func
        
        # 初始化变量
        for var in bot.variables:
            if var.initial_value:
                value = self.evaluate(var.initial_value)
            else:
                value = None
            self.env.define(var.name, value)
        
        # 设置初始状态
        if bot.initial_state and bot.initial_state in self.states:
            self.current_state = self.states[bot.initial_state]
        elif bot.states:
            # 找到标记为initial的状态，或使用第一个状态
            for state in bot.states:
                if state.is_initial:
                    self.current_state = state
                    break
            else:
                self.current_state = bot.states[0]
        
        self.execution_state = ExecutionState.RUNNING
    
    def start(self):
        """启动机器人，执行初始状态的on_enter"""
        if self.current_state:
            self._execute_state_enter()
    
    def _execute_state_enter(self):
        """执行当前状态的on_enter处理器"""
        for handler in self.current_state.handlers:
            if handler.event_type == 'on_enter':
                try:
                    self.execute_statements(handler.statements)
                except GotoException as e:
                    self._goto_state(e.state_name)
                break
    
    def _execute_state_exit(self):
        """执行当前状态的on_exit处理器"""
        for handler in self.current_state.handlers:
            if handler.event_type == 'on_exit':
                self.execute_statements(handler.statements)
                break
    
    def _goto_state(self, state_name: str):
        """跳转到指定状态"""
        if state_name not in self.states:
            raise RuntimeError(f"未定义的状态: {state_name}")
        
        # 执行当前状态的on_exit
        if self.current_state:
            self._execute_state_exit()
        
        # 切换状态
        self.current_state = self.states[state_name]
        
        # 检查是否是结束状态
        if self.current_state.is_final:
            self.execution_state = ExecutionState.FINISHED
        
        # 执行新状态的on_enter
        self._execute_state_enter()
    
    def process_input(self, user_input: str) -> Tuple[str, bool]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
        
        Returns:
            (响应文本, 是否继续)
        """
        if self.execution_state == ExecutionState.FINISHED:
            return "对话已结束", False
        
        if not self.current_state:
            return "机器人未正确初始化", False
        
        # 存储用户输入
        self.env.set('_user_input', user_input)
        
        # 意图识别
        intent_infos = [
            IntentInfo(
                name=intent.name,
                patterns=intent.patterns,
                description=intent.description,
                examples=intent.examples
            )
            for intent in self.intents.values()
        ]
        
        context = {
            'current_state': self.current_state.name,
            'variables': {k: v for k, v in self.env.variables.items() if not k.startswith('_')}
        }
        
        intent_result = self.llm.recognize_intent(user_input, intent_infos, context)
        
        # 存储识别结果
        self.env.set('_intent', intent_result.intent_name)
        self.env.set('_confidence', intent_result.confidence)
        self.env.set('_entities', intent_result.extracted_entities)
        
        # 收集输出
        outputs = []
        original_say = self.io.output_callback
        self.io.output_callback = lambda msg: outputs.append(msg)
        
        try:
            # 尝试匹配转换规则
            matched = False
            for transition in self.current_state.transitions:
                if transition.intent_name == intent_result.intent_name:
                    # 检查条件
                    if transition.condition:
                        if not self.evaluate(transition.condition):
                            continue
                    
                    matched = True
                    self._goto_state(transition.target_state)
                    break
            
            # 如果没有匹配，执行fallback
            if not matched:
                if self.current_state.fallback:
                    self.execute_statements(self.current_state.fallback.statements)
                else:
                    outputs.append("抱歉，我没有理解您的意思，请再说一遍。")
        
        except GotoException as e:
            self._goto_state(e.state_name)
        
        finally:
            self.io.output_callback = original_say
        
        response = "\n".join(outputs) if outputs else ""
        continue_conversation = self.execution_state != ExecutionState.FINISHED
        
        return response, continue_conversation
    
    def execute_statements(self, statements: List[Statement]):
        """执行语句列表"""
        for stmt in statements:
            self.execute_statement(stmt)
    
    def execute_statement(self, stmt: Statement):
        """执行单个语句"""
        if isinstance(stmt, SayStatement):
            message = self.evaluate(stmt.message)
            self.io.say(str(message))
        
        elif isinstance(stmt, AskStatement):
            prompt = self.evaluate(stmt.prompt)
            response = self.io.ask(str(prompt))
            self.env.set(stmt.variable, response)
        
        elif isinstance(stmt, SetStatement):
            value = self.evaluate(stmt.value)
            self.env.set(stmt.variable, value)
        
        elif isinstance(stmt, GotoStatement):
            raise GotoException(stmt.state_name)
        
        elif isinstance(stmt, CallStatement):
            self.evaluate(stmt.function_call)
        
        elif isinstance(stmt, ReturnStatement):
            value = self.evaluate(stmt.value) if stmt.value else None
            raise ReturnException(value)
        
        elif isinstance(stmt, IfStatement):
            self._execute_if(stmt)
        
        elif isinstance(stmt, WhileStatement):
            self._execute_while(stmt)
        
        elif isinstance(stmt, ForStatement):
            self._execute_for(stmt)
        
        elif isinstance(stmt, ExpressionStatement):
            self.evaluate(stmt.expression)
        
        else:
            raise RuntimeError(f"未知的语句类型: {type(stmt)}")
    
    def _execute_if(self, stmt: IfStatement):
        """执行if语句"""
        if self.evaluate(stmt.condition):
            self.execute_statements(stmt.then_block)
        else:
            for condition, block in stmt.elif_blocks:
                if self.evaluate(condition):
                    self.execute_statements(block)
                    return
            if stmt.else_block:
                self.execute_statements(stmt.else_block)
    
    def _execute_while(self, stmt: WhileStatement):
        """执行while语句"""
        max_iterations = 10000  # 防止无限循环
        count = 0
        while self.evaluate(stmt.condition):
            self.execute_statements(stmt.body)
            count += 1
            if count >= max_iterations:
                raise RuntimeError("循环次数过多，可能是无限循环")
    
    def _execute_for(self, stmt: ForStatement):
        """执行for语句"""
        iterable = self.evaluate(stmt.iterable)
        if not hasattr(iterable, '__iter__'):
            raise RuntimeError(f"不可迭代的对象: {type(iterable)}")
        
        for item in iterable:
            self.env.define(stmt.variable, item)
            self.execute_statements(stmt.body)
    
    def evaluate(self, expr: Expression) -> Any:
        """求值表达式"""
        if expr is None:
            return None
        
        if isinstance(expr, StringLiteral):
            return expr.value
        
        elif isinstance(expr, NumberLiteral):
            return expr.value
        
        elif isinstance(expr, BooleanLiteral):
            return expr.value
        
        elif isinstance(expr, ListLiteral):
            return [self.evaluate(e) for e in expr.elements]
        
        elif isinstance(expr, Identifier):
            try:
                return self.env.get(expr.name)
            except NameError:
                # 可能是内置函数名
                if expr.name in self.builtins:
                    return self.builtins[expr.name]
                raise
        
        elif isinstance(expr, BinaryOp):
            return self._evaluate_binary_op(expr)
        
        elif isinstance(expr, UnaryOp):
            return self._evaluate_unary_op(expr)
        
        elif isinstance(expr, FunctionCall):
            return self._evaluate_function_call(expr)
        
        elif isinstance(expr, MemberAccess):
            obj = self.evaluate(expr.object)
            if isinstance(obj, dict):
                return obj.get(expr.member)
            return getattr(obj, expr.member, None)
        
        elif isinstance(expr, IndexAccess):
            obj = self.evaluate(expr.object)
            index = self.evaluate(expr.index)
            return obj[index]
        
        else:
            raise RuntimeError(f"未知的表达式类型: {type(expr)}")
    
    def _evaluate_binary_op(self, expr: BinaryOp) -> Any:
        """求值二元运算"""
        left = self.evaluate(expr.left)
        
        # 短路求值
        if expr.operator == 'and':
            return left and self.evaluate(expr.right)
        elif expr.operator == 'or':
            return left or self.evaluate(expr.right)
        
        right = self.evaluate(expr.right)
        
        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b if b != 0 else 0,
            '%': lambda a, b: a % b if b != 0 else 0,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '<': lambda a, b: a < b,
            '>': lambda a, b: a > b,
            '<=': lambda a, b: a <= b,
            '>=': lambda a, b: a >= b,
        }
        
        if expr.operator in ops:
            return ops[expr.operator](left, right)
        
        raise RuntimeError(f"未知的运算符: {expr.operator}")
    
    def _evaluate_unary_op(self, expr: UnaryOp) -> Any:
        """求值一元运算"""
        operand = self.evaluate(expr.operand)
        
        if expr.operator == 'not':
            return not operand
        elif expr.operator == '-':
            return -operand
        
        raise RuntimeError(f"未知的一元运算符: {expr.operator}")
    
    def _evaluate_function_call(self, expr: FunctionCall) -> Any:
        """求值函数调用"""
        # 检查内置函数
        if expr.name in self.builtins:
            args = [self.evaluate(arg) for arg in expr.arguments]
            return self.builtins[expr.name](*args)
        
        # 检查用户定义的函数
        func_def = self.env.get_function(expr.name)
        if func_def:
            return self._call_user_function(func_def, expr.arguments)
        
        raise RuntimeError(f"未定义的函数: {expr.name}")
    
    def _call_user_function(self, func: FunctionDef, args: List[Expression]) -> Any:
        """调用用户定义的函数"""
        # 创建新的作用域
        local_env = Environment(parent=self.env)
        
        # 绑定参数
        for i, param in enumerate(func.parameters):
            if i < len(args):
                value = self.evaluate(args[i])
            elif param.default_value:
                value = self.evaluate(param.default_value)
            else:
                value = None
            local_env.define(param.name, value)
        
        # 保存当前环境并切换
        old_env = self.env
        self.env = local_env
        
        try:
            self.execute_statements(func.body)
            return None
        except ReturnException as e:
            return e.value
        finally:
            self.env = old_env


# 便捷函数
def run_bot(program: Program, io_handler: Optional[IOHandler] = None) -> Interpreter:
    """运行机器人"""
    interpreter = Interpreter(io_handler)
    interpreter.load_program(program)
    interpreter.start()
    return interpreter


# 测试代码
if __name__ == '__main__':
    from .parser import parse
    
    test_code = '''
    bot "测试客服" {
        intent 问候 {
            patterns: ["你好", "hi", "hello"]
            description: "用户打招呼"
        }
        
        intent 告别 {
            patterns: ["再见", "拜拜", "goodbye"]
            description: "用户告别"
        }
        
        state 欢迎 initial {
            on_enter {
                say "您好！我是测试客服。"
            }
            when 告别 -> 结束
            fallback {
                say "请问有什么可以帮助您？"
            }
        }
        
        state 结束 final {
            on_enter {
                say "再见，祝您生活愉快！"
            }
        }
    }
    '''
    
    program = parse(test_code)
    if program:
        interpreter = Interpreter()
        interpreter.load_program(program)
        interpreter.start()
        
        # 模拟对话
        test_inputs = ["你好", "再见"]
        for user_input in test_inputs:
            print(f"\n用户: {user_input}")
            response, continue_chat = interpreter.process_input(user_input)
            print(f"机器人: {response}")
            if not continue_chat:
                break
