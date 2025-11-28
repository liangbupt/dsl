"""
词法分析器模块

使用PLY实现DSL的词法分析，将源代码转换为Token序列。
"""

import ply.lex as lex
from typing import List, Tuple


class BotLexer:
    """智能客服机器人DSL词法分析器"""
    
    # 保留字
    reserved = {
        # 结构关键字
        'bot': 'BOT',
        'intent': 'INTENT',
        'state': 'STATE',
        'var': 'VAR',
        'func': 'FUNC',
        
        # 状态修饰符
        'initial': 'INITIAL',
        'final': 'FINAL',
        
        # 事件处理
        'on_enter': 'ON_ENTER',
        'on_exit': 'ON_EXIT',
        'on_message': 'ON_MESSAGE',
        
        # 转换关键字
        'when': 'WHEN',
        'fallback': 'FALLBACK',
        
        # 动作关键字
        'say': 'SAY',
        'ask': 'ASK',
        'set': 'SET',
        'goto': 'GOTO',
        'call': 'CALL',
        'return': 'RETURN',
        
        # 控制流
        'if': 'IF',
        'elif': 'ELIF',
        'else': 'ELSE',
        'while': 'WHILE',
        'for': 'FOR',
        'in': 'IN',
        'break': 'BREAK',
        'continue': 'CONTINUE',
        
        # 布尔值
        'true': 'TRUE',
        'false': 'FALSE',
        'null': 'NULL',
        
        # 逻辑运算符
        'and': 'AND',
        'or': 'OR',
        'not': 'NOT',
        
        # 属性关键字
        'patterns': 'PATTERNS',
        'description': 'DESCRIPTION',
        'examples': 'EXAMPLES',
    }
    
    # Token列表
    tokens = [
        # 字面量
        'STRING',
        'NUMBER',
        'IDENTIFIER',
        
        # 运算符
        'PLUS',          # +
        'MINUS',         # -
        'TIMES',         # *
        'DIVIDE',        # /
        'MODULO',        # %
        
        # 比较运算符
        'EQ',            # ==
        'NE',            # !=
        'LT',            # <
        'GT',            # >
        'LE',            # <=
        'GE',            # >=
        
        # 赋值
        'ASSIGN',        # =
        
        # 箭头
        'ARROW',         # ->
        
        # 分隔符
        'LPAREN',        # (
        'RPAREN',        # )
        'LBRACE',        # {
        'RBRACE',        # }
        'LBRACKET',      # [
        'RBRACKET',      # ]
        'COMMA',         # ,
        'COLON',         # :
        'SEMICOLON',     # ;
        'DOT',           # .
        
        # 注释
        'COMMENT',
    ] + list(reserved.values())
    
    # 忽略空白字符
    t_ignore = ' \t'
    
    # 简单Token规则
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_MODULO = r'%'
    
    t_EQ = r'=='
    t_NE = r'!='
    t_LE = r'<='
    t_GE = r'>='
    t_LT = r'<'
    t_GT = r'>'
    
    t_ASSIGN = r'='
    t_ARROW = r'->'
    
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_COMMA = r','
    t_COLON = r':'
    t_SEMICOLON = r';'
    t_DOT = r'\.'
    
    def __init__(self):
        self.lexer = None
        self.errors: List[Tuple[int, int, str]] = []
    
    def t_COMMENT(self, t):
        r'\#[^\n]*'
        pass  # 忽略注释
    
    def t_STRING(self, t):
        r'\"([^\\\n]|(\\.))*?\"|\'([^\\\n]|(\\.))*?\''
        # 处理转义字符
        value = t.value[1:-1]  # 去掉引号
        value = value.replace('\\n', '\n')
        value = value.replace('\\t', '\t')
        value = value.replace('\\"', '"')
        value = value.replace("\\'", "'")
        value = value.replace('\\\\', '\\')
        t.value = value
        return t
    
    def t_NUMBER(self, t):
        r'\d+(\.\d+)?'
        if '.' in t.value:
            t.value = float(t.value)
        else:
            t.value = int(t.value)
        return t
    
    def t_IDENTIFIER(self, t):
        r'[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*'
        # 检查是否是保留字
        t.type = self.reserved.get(t.value, 'IDENTIFIER')
        return t
    
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
    
    def t_error(self, t):
        """错误处理"""
        line = t.lexer.lineno
        col = self._find_column(t.lexer.lexdata, t)
        self.errors.append((line, col, f"非法字符 '{t.value[0]}'"))
        t.lexer.skip(1)
    
    def _find_column(self, input_text, token):
        """计算Token的列号"""
        line_start = input_text.rfind('\n', 0, token.lexpos) + 1
        return token.lexpos - line_start + 1
    
    def build(self, **kwargs):
        """构建词法分析器"""
        self.lexer = lex.lex(module=self, **kwargs)
        return self.lexer
    
    def tokenize(self, data: str) -> List:
        """对输入进行词法分析"""
        self.errors = []
        self.lexer.input(data)
        tokens = []
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            tokens.append(tok)
        return tokens
    
    def reset(self):
        """重置分析器状态"""
        self.errors = []
        if self.lexer:
            self.lexer.lineno = 1


# 全局词法分析器实例
_lexer_instance = None

def get_lexer():
    """获取词法分析器实例"""
    global _lexer_instance
    if _lexer_instance is None:
        _lexer_instance = BotLexer()
        _lexer_instance.build()
    return _lexer_instance


def tokenize(source: str) -> List:
    """便捷函数：对源代码进行词法分析"""
    lexer = get_lexer()
    lexer.reset()
    return lexer.tokenize(source)


# 测试代码
if __name__ == '__main__':
    test_code = '''
    # 这是一个测试
    bot "电商客服" {
        intent 查询订单 {
            patterns: ["订单", "物流", "快递"]
            description: "用户想查询订单"
        }
        
        state 初始状态 initial {
            on_enter {
                say "您好，欢迎使用智能客服！"
            }
            
            when 查询订单 -> 订单查询
            
            fallback {
                say "抱歉，我没理解您的意思"
            }
        }
        
        var order_id = ""
        var count = 0
        
        func validate(id) {
            if length(id) == 10 {
                return true
            }
            return false
        }
    }
    '''
    
    lexer = BotLexer()
    lexer.build()
    tokens = lexer.tokenize(test_code)
    
    print("Tokens:")
    for tok in tokens:
        print(f"  {tok}")
    
    if lexer.errors:
        print("\nErrors:")
        for line, col, msg in lexer.errors:
            print(f"  Line {line}, Col {col}: {msg}")
