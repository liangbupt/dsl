"""
语法分析器模块

使用PLY实现DSL的语法分析，将Token序列转换为AST。
"""

import ply.yacc as yacc
from .lexer import BotLexer
from .ast_nodes import (
    Program, BotDef, IntentDef, StateDef, VariableDef, FunctionDef,
    ParameterDef, EventHandler, TransitionRule, FallbackHandler,
    Statement, SayStatement, AskStatement, SetStatement, GotoStatement,
    CallStatement, ReturnStatement, IfStatement, WhileStatement, ForStatement,
    ExpressionStatement,
    Expression, StringLiteral, NumberLiteral, BooleanLiteral, ListLiteral,
    Identifier, BinaryOp, UnaryOp, FunctionCall, MemberAccess, IndexAccess
)
from typing import List, Tuple, Optional


class BotParser:
    """智能客服机器人DSL语法分析器"""
    
    def __init__(self):
        self.lexer = BotLexer()
        self.lexer.build()
        self.tokens = self.lexer.tokens
        self.parser = None
        self.errors: List[Tuple[int, str]] = []
    
    # ============ 优先级定义 ============
    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('right', 'NOT'),
        ('left', 'EQ', 'NE'),
        ('left', 'LT', 'GT', 'LE', 'GE'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MODULO'),
        ('right', 'UMINUS'),
    )
    
    # ============ 顶层规则 ============
    
    def p_program(self, p):
        '''program : bot_list'''
        p[0] = Program(bots=p[1])
    
    def p_bot_list(self, p):
        '''bot_list : bot_list bot_def
                    | bot_def'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1]]
    
    def p_bot_def(self, p):
        '''bot_def : BOT STRING LBRACE bot_body RBRACE'''
        intents, states, variables, functions = [], [], [], []
        initial_state = None
        
        for item in p[4]:
            if isinstance(item, IntentDef):
                intents.append(item)
            elif isinstance(item, StateDef):
                states.append(item)
                if item.is_initial:
                    initial_state = item.name
            elif isinstance(item, VariableDef):
                variables.append(item)
            elif isinstance(item, FunctionDef):
                functions.append(item)
        
        p[0] = BotDef(
            name=p[2],
            intents=intents,
            states=states,
            variables=variables,
            functions=functions,
            initial_state=initial_state,
            line=p.lineno(1)
        )
    
    def p_bot_body(self, p):
        '''bot_body : bot_body bot_member
                    | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []
    
    def p_bot_member(self, p):
        '''bot_member : intent_def
                      | state_def
                      | variable_def
                      | function_def'''
        p[0] = p[1]
    
    # ============ 意图定义 ============
    
    def p_intent_def(self, p):
        '''intent_def : INTENT IDENTIFIER LBRACE intent_body RBRACE'''
        patterns = []
        description = ""
        examples = []
        
        for key, value in p[4]:
            if key == 'patterns':
                patterns = value
            elif key == 'description':
                description = value
            elif key == 'examples':
                examples = value
        
        p[0] = IntentDef(
            name=p[2],
            patterns=patterns,
            description=description,
            examples=examples,
            line=p.lineno(1)
        )
    
    def p_intent_body(self, p):
        '''intent_body : intent_body intent_attr
                       | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []
    
    def p_intent_attr(self, p):
        '''intent_attr : PATTERNS COLON string_list
                       | DESCRIPTION COLON STRING
                       | EXAMPLES COLON string_list'''
        if p[1] == 'patterns':
            p[0] = ('patterns', p[3])
        elif p[1] == 'description':
            p[0] = ('description', p[3])
        elif p[1] == 'examples':
            p[0] = ('examples', p[3])
    
    def p_string_list(self, p):
        '''string_list : LBRACKET string_items RBRACKET
                       | LBRACKET RBRACKET'''
        if len(p) == 4:
            p[0] = p[2]
        else:
            p[0] = []
    
    def p_string_items(self, p):
        '''string_items : string_items COMMA STRING
                        | STRING'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]
    
    # ============ 状态定义 ============
    
    def p_state_def(self, p):
        '''state_def : STATE IDENTIFIER state_modifiers LBRACE state_body RBRACE'''
        handlers, transitions, fallback = [], [], None
        
        for item in p[5]:
            if isinstance(item, EventHandler):
                handlers.append(item)
            elif isinstance(item, TransitionRule):
                transitions.append(item)
            elif isinstance(item, FallbackHandler):
                fallback = item
        
        p[0] = StateDef(
            name=p[2],
            is_initial='initial' in p[3],
            is_final='final' in p[3],
            handlers=handlers,
            transitions=transitions,
            fallback=fallback,
            line=p.lineno(1)
        )
    
    def p_state_modifiers(self, p):
        '''state_modifiers : state_modifiers state_modifier
                           | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []
    
    def p_state_modifier(self, p):
        '''state_modifier : INITIAL
                          | FINAL'''
        p[0] = p[1]
    
    def p_state_body(self, p):
        '''state_body : state_body state_member
                      | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []
    
    def p_state_member(self, p):
        '''state_member : event_handler
                        | transition_rule
                        | fallback_handler'''
        p[0] = p[1]
    
    def p_event_handler(self, p):
        '''event_handler : ON_ENTER LBRACE statement_list RBRACE
                         | ON_EXIT LBRACE statement_list RBRACE
                         | ON_MESSAGE LBRACE statement_list RBRACE'''
        p[0] = EventHandler(
            event_type=p[1],
            statements=p[3],
            line=p.lineno(1)
        )
    
    def p_transition_rule(self, p):
        '''transition_rule : WHEN IDENTIFIER ARROW IDENTIFIER
                           | WHEN IDENTIFIER ARROW IDENTIFIER IF expression'''
        if len(p) == 5:
            p[0] = TransitionRule(
                intent_name=p[2],
                target_state=p[4],
                line=p.lineno(1)
            )
        else:
            p[0] = TransitionRule(
                intent_name=p[2],
                target_state=p[4],
                condition=p[6],
                line=p.lineno(1)
            )
    
    def p_fallback_handler(self, p):
        '''fallback_handler : FALLBACK LBRACE statement_list RBRACE'''
        p[0] = FallbackHandler(
            statements=p[3],
            line=p.lineno(1)
        )
    
    # ============ 变量定义 ============
    
    def p_variable_def(self, p):
        '''variable_def : VAR IDENTIFIER ASSIGN expression
                        | VAR IDENTIFIER'''
        if len(p) == 5:
            p[0] = VariableDef(
                name=p[2],
                initial_value=p[4],
                line=p.lineno(1)
            )
        else:
            p[0] = VariableDef(
                name=p[2],
                line=p.lineno(1)
            )
    
    # ============ 函数定义 ============
    
    def p_function_def(self, p):
        '''function_def : FUNC IDENTIFIER LPAREN param_list RPAREN LBRACE statement_list RBRACE'''
        p[0] = FunctionDef(
            name=p[2],
            parameters=p[4],
            body=p[7],
            line=p.lineno(1)
        )
    
    def p_param_list(self, p):
        '''param_list : param_list COMMA param
                      | param
                      | empty'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        elif len(p) == 2 and p[1] is not None:
            p[0] = [p[1]]
        else:
            p[0] = []
    
    def p_param(self, p):
        '''param : IDENTIFIER
                 | IDENTIFIER ASSIGN expression'''
        if len(p) == 2:
            p[0] = ParameterDef(name=p[1])
        else:
            p[0] = ParameterDef(name=p[1], default_value=p[3])
    
    # ============ 语句 ============
    
    def p_statement_list(self, p):
        '''statement_list : statement_list statement
                          | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []
    
    def p_statement(self, p):
        '''statement : say_statement
                     | ask_statement
                     | set_statement
                     | goto_statement
                     | call_statement
                     | return_statement
                     | if_statement
                     | while_statement
                     | for_statement
                     | expression_statement'''
        p[0] = p[1]
    
    def p_say_statement(self, p):
        '''say_statement : SAY expression'''
        p[0] = SayStatement(message=p[2], line=p.lineno(1))
    
    def p_ask_statement(self, p):
        '''ask_statement : ASK expression ARROW IDENTIFIER'''
        p[0] = AskStatement(prompt=p[2], variable=p[4], line=p.lineno(1))
    
    def p_set_statement(self, p):
        '''set_statement : SET IDENTIFIER ASSIGN expression'''
        p[0] = SetStatement(variable=p[2], value=p[4], line=p.lineno(1))
    
    def p_goto_statement(self, p):
        '''goto_statement : GOTO IDENTIFIER'''
        p[0] = GotoStatement(state_name=p[2], line=p.lineno(1))
    
    def p_call_statement(self, p):
        '''call_statement : CALL function_call'''
        p[0] = CallStatement(function_call=p[2], line=p.lineno(1))
    
    def p_return_statement(self, p):
        '''return_statement : RETURN expression
                            | RETURN'''
        if len(p) == 3:
            p[0] = ReturnStatement(value=p[2], line=p.lineno(1))
        else:
            p[0] = ReturnStatement(line=p.lineno(1))
    
    def p_if_statement(self, p):
        '''if_statement : IF expression LBRACE statement_list RBRACE elif_list else_clause'''
        p[0] = IfStatement(
            condition=p[2],
            then_block=p[4],
            elif_blocks=p[6],
            else_block=p[7],
            line=p.lineno(1)
        )
    
    def p_elif_list(self, p):
        '''elif_list : elif_list ELIF expression LBRACE statement_list RBRACE
                     | empty'''
        if len(p) == 7:
            p[0] = p[1] + [(p[3], p[5])]
        else:
            p[0] = []
    
    def p_else_clause(self, p):
        '''else_clause : ELSE LBRACE statement_list RBRACE
                       | empty'''
        if len(p) == 5:
            p[0] = p[3]
        else:
            p[0] = None
    
    def p_while_statement(self, p):
        '''while_statement : WHILE expression LBRACE statement_list RBRACE'''
        p[0] = WhileStatement(
            condition=p[2],
            body=p[4],
            line=p.lineno(1)
        )
    
    def p_for_statement(self, p):
        '''for_statement : FOR IDENTIFIER IN expression LBRACE statement_list RBRACE'''
        p[0] = ForStatement(
            variable=p[2],
            iterable=p[4],
            body=p[6],
            line=p.lineno(1)
        )
    
    def p_expression_statement(self, p):
        '''expression_statement : expression'''
        p[0] = ExpressionStatement(expression=p[1], line=p.lineno(1))
    
    # ============ 表达式 ============
    
    def p_expression(self, p):
        '''expression : or_expr'''
        p[0] = p[1]
    
    def p_or_expr(self, p):
        '''or_expr : or_expr OR and_expr
                   | and_expr'''
        if len(p) == 4:
            p[0] = BinaryOp(operator='or', left=p[1], right=p[3], line=p.lineno(2))
        else:
            p[0] = p[1]
    
    def p_and_expr(self, p):
        '''and_expr : and_expr AND not_expr
                    | not_expr'''
        if len(p) == 4:
            p[0] = BinaryOp(operator='and', left=p[1], right=p[3], line=p.lineno(2))
        else:
            p[0] = p[1]
    
    def p_not_expr(self, p):
        '''not_expr : NOT not_expr
                    | comparison'''
        if len(p) == 3:
            p[0] = UnaryOp(operator='not', operand=p[2], line=p.lineno(1))
        else:
            p[0] = p[1]
    
    def p_comparison(self, p):
        '''comparison : additive EQ additive
                      | additive NE additive
                      | additive LT additive
                      | additive GT additive
                      | additive LE additive
                      | additive GE additive
                      | additive'''
        if len(p) == 4:
            p[0] = BinaryOp(operator=p[2], left=p[1], right=p[3], line=p.lineno(2))
        else:
            p[0] = p[1]
    
    def p_additive(self, p):
        '''additive : additive PLUS multiplicative
                    | additive MINUS multiplicative
                    | multiplicative'''
        if len(p) == 4:
            p[0] = BinaryOp(operator=p[2], left=p[1], right=p[3], line=p.lineno(2))
        else:
            p[0] = p[1]
    
    def p_multiplicative(self, p):
        '''multiplicative : multiplicative TIMES unary
                          | multiplicative DIVIDE unary
                          | multiplicative MODULO unary
                          | unary'''
        if len(p) == 4:
            p[0] = BinaryOp(operator=p[2], left=p[1], right=p[3], line=p.lineno(2))
        else:
            p[0] = p[1]
    
    def p_unary(self, p):
        '''unary : MINUS unary %prec UMINUS
                 | postfix'''
        if len(p) == 3:
            p[0] = UnaryOp(operator='-', operand=p[2], line=p.lineno(1))
        else:
            p[0] = p[1]
    
    def p_postfix(self, p):
        '''postfix : postfix DOT IDENTIFIER
                   | postfix LBRACKET expression RBRACKET
                   | postfix LPAREN arg_list RPAREN
                   | primary'''
        if len(p) == 4:
            p[0] = MemberAccess(object=p[1], member=p[3], line=p.lineno(2))
        elif len(p) == 5:
            if p[2] == '[':
                p[0] = IndexAccess(object=p[1], index=p[3], line=p.lineno(2))
            else:
                # 函数调用
                if isinstance(p[1], Identifier):
                    p[0] = FunctionCall(name=p[1].name, arguments=p[3], line=p.lineno(2))
                else:
                    # 方法调用
                    p[0] = FunctionCall(name=str(p[1]), arguments=p[3], line=p.lineno(2))
        else:
            p[0] = p[1]
    
    def p_function_call(self, p):
        '''function_call : IDENTIFIER LPAREN arg_list RPAREN'''
        p[0] = FunctionCall(name=p[1], arguments=p[3], line=p.lineno(1))
    
    def p_arg_list(self, p):
        '''arg_list : arg_list COMMA expression
                    | expression
                    | empty'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        elif len(p) == 2 and p[1] is not None:
            p[0] = [p[1]]
        else:
            p[0] = []
    
    def p_primary(self, p):
        '''primary : STRING
                   | NUMBER
                   | TRUE
                   | FALSE
                   | NULL
                   | IDENTIFIER
                   | list_literal
                   | LPAREN expression RPAREN'''
        if len(p) == 2:
            if isinstance(p[1], str):
                if p.slice[1].type == 'STRING':
                    p[0] = StringLiteral(value=p[1], line=p.lineno(1))
                elif p.slice[1].type == 'IDENTIFIER':
                    p[0] = Identifier(name=p[1], line=p.lineno(1))
                else:
                    p[0] = p[1]
            elif isinstance(p[1], bool) or p[1] is True:
                p[0] = BooleanLiteral(value=True, line=p.lineno(1))
            elif p[1] is False:
                p[0] = BooleanLiteral(value=False, line=p.lineno(1))
            elif p[1] is None:
                p[0] = BooleanLiteral(value=None, line=p.lineno(1))
            elif isinstance(p[1], (int, float)):
                p[0] = NumberLiteral(value=p[1], line=p.lineno(1))
            elif isinstance(p[1], ListLiteral):
                p[0] = p[1]
            else:
                p[0] = p[1]
        else:
            p[0] = p[2]
    
    def p_list_literal(self, p):
        '''list_literal : LBRACKET expression_list RBRACKET
                        | LBRACKET RBRACKET'''
        if len(p) == 4:
            p[0] = ListLiteral(elements=p[2], line=p.lineno(1))
        else:
            p[0] = ListLiteral(elements=[], line=p.lineno(1))
    
    def p_expression_list(self, p):
        '''expression_list : expression_list COMMA expression
                           | expression'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]
    
    def p_empty(self, p):
        '''empty :'''
        p[0] = None
    
    def p_error(self, p):
        """语法错误处理"""
        if p:
            self.errors.append((p.lineno, f"语法错误: 意外的 '{p.value}'"))
        else:
            self.errors.append((0, "语法错误: 意外的文件结尾"))
    
    def build(self, **kwargs):
        """构建语法分析器"""
        self.parser = yacc.yacc(module=self, **kwargs)
        return self.parser
    
    def parse(self, source: str) -> Optional[Program]:
        """解析源代码"""
        self.errors = []
        self.lexer.reset()
        result = self.parser.parse(source, lexer=self.lexer.lexer)
        return result


# 全局解析器实例
_parser_instance = None

def get_parser():
    """获取解析器实例"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = BotParser()
        _parser_instance.build(debug=False, write_tables=False)
    return _parser_instance


def parse(source: str) -> Optional[Program]:
    """便捷函数：解析源代码"""
    parser = get_parser()
    return parser.parse(source)


# 测试代码
if __name__ == '__main__':
    from ast_nodes import pretty_print
    
    test_code = '''
    bot "测试客服" {
        intent 问候 {
            patterns: ["你好", "hi", "hello"]
            description: "用户打招呼"
        }
        
        state 初始 initial {
            on_enter {
                say "欢迎！"
            }
            when 问候 -> 欢迎状态
        }
        
        var name = ""
        
        func greet(n) {
            say "你好，" + n
        }
    }
    '''
    
    parser = BotParser()
    parser.build(debug=False, write_tables=False)
    
    ast = parser.parse(test_code)
    
    if parser.errors:
        print("Errors:")
        for line, msg in parser.errors:
            print(f"  Line {line}: {msg}")
    else:
        print("AST:")
        print(pretty_print(ast))
