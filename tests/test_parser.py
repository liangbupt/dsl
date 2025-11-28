"""
测试模块

包含词法分析器、语法分析器和解释器的单元测试。
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from src.lexer import BotLexer, tokenize
from src.parser import BotParser
from src.ast_nodes import Program, BotDef, IntentDef, StateDef


class TestLexer(unittest.TestCase):
    """词法分析器测试"""
    
    def setUp(self):
        self.lexer = BotLexer()
        self.lexer.build()
    
    def test_keywords(self):
        """测试关键字识别"""
        code = "bot intent state var func"
        tokens = self.lexer.tokenize(code)
        types = [t.type for t in tokens]
        self.assertEqual(types, ['BOT', 'INTENT', 'STATE', 'VAR', 'FUNC'])
    
    def test_string_literal(self):
        """测试字符串字面量"""
        code = '"hello world" \'single quotes\''
        tokens = self.lexer.tokenize(code)
        self.assertEqual(tokens[0].type, 'STRING')
        self.assertEqual(tokens[0].value, 'hello world')
        self.assertEqual(tokens[1].value, 'single quotes')
    
    def test_number_literal(self):
        """测试数字字面量"""
        code = "42 3.14"
        tokens = self.lexer.tokenize(code)
        self.assertEqual(tokens[0].value, 42)
        self.assertEqual(tokens[1].value, 3.14)
    
    def test_chinese_identifier(self):
        """测试中文标识符"""
        code = "state 初始状态 { }"
        tokens = self.lexer.tokenize(code)
        self.assertEqual(tokens[0].type, 'STATE')
        self.assertEqual(tokens[1].type, 'IDENTIFIER')
        self.assertEqual(tokens[1].value, '初始状态')
    
    def test_operators(self):
        """测试运算符"""
        code = "+ - * / == != < > <= >= ->"
        tokens = self.lexer.tokenize(code)
        types = [t.type for t in tokens]
        expected = ['PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'EQ', 'NE', 
                   'LT', 'GT', 'LE', 'GE', 'ARROW']
        self.assertEqual(types, expected)
    
    def test_comment(self):
        """测试注释"""
        code = "bot # this is a comment\nintent"
        tokens = self.lexer.tokenize(code)
        types = [t.type for t in tokens]
        self.assertEqual(types, ['BOT', 'INTENT'])


class TestParser(unittest.TestCase):
    """语法分析器测试"""
    
    def setUp(self):
        self.parser = BotParser()
        self.parser.build(debug=False, write_tables=False)
    
    def test_simple_bot(self):
        """测试简单机器人定义"""
        code = '''
        bot "测试" {
        }
        '''
        result = self.parser.parse(code)
        self.assertIsInstance(result, Program)
        self.assertEqual(len(result.bots), 1)
        self.assertEqual(result.bots[0].name, "测试")
    
    def test_intent_definition(self):
        """测试意图定义"""
        code = '''
        bot "测试" {
            intent 问候 {
                patterns: ["你好", "hi"]
                description: "用户打招呼"
            }
        }
        '''
        result = self.parser.parse(code)
        bot = result.bots[0]
        self.assertEqual(len(bot.intents), 1)
        intent = bot.intents[0]
        self.assertEqual(intent.name, "问候")
        self.assertEqual(intent.patterns, ["你好", "hi"])
    
    def test_state_definition(self):
        """测试状态定义"""
        code = '''
        bot "测试" {
            state 初始 initial {
                on_enter {
                    say "欢迎"
                }
            }
        }
        '''
        result = self.parser.parse(code)
        bot = result.bots[0]
        self.assertEqual(len(bot.states), 1)
        state = bot.states[0]
        self.assertEqual(state.name, "初始")
        self.assertTrue(state.is_initial)
    
    def test_variable_definition(self):
        """测试变量定义"""
        code = '''
        bot "测试" {
            var name = "张三"
            var count = 0
        }
        '''
        result = self.parser.parse(code)
        bot = result.bots[0]
        self.assertEqual(len(bot.variables), 2)
    
    def test_function_definition(self):
        """测试函数定义"""
        code = '''
        bot "测试" {
            func greet(name) {
                say "你好 " + name
            }
        }
        '''
        result = self.parser.parse(code)
        bot = result.bots[0]
        self.assertEqual(len(bot.functions), 1)
        func = bot.functions[0]
        self.assertEqual(func.name, "greet")
        self.assertEqual(len(func.parameters), 1)
    
    def test_transition_rule(self):
        """测试状态转换规则"""
        code = '''
        bot "测试" {
            state 初始 initial {
                when 问候 -> 欢迎
            }
        }
        '''
        result = self.parser.parse(code)
        state = result.bots[0].states[0]
        self.assertEqual(len(state.transitions), 1)
        trans = state.transitions[0]
        self.assertEqual(trans.intent_name, "问候")
        self.assertEqual(trans.target_state, "欢迎")
    
    def test_if_statement(self):
        """测试if语句"""
        code = '''
        bot "测试" {
            state 测试 {
                on_enter {
                    if x > 0 {
                        say "正数"
                    } elif x < 0 {
                        say "负数"
                    } else {
                        say "零"
                    }
                }
            }
        }
        '''
        result = self.parser.parse(code)
        self.assertIsNotNone(result)
        self.assertEqual(len(self.parser.errors), 0)


class TestExpressions(unittest.TestCase):
    """表达式测试"""
    
    def setUp(self):
        self.parser = BotParser()
        self.parser.build(debug=False, write_tables=False)
    
    def test_binary_operations(self):
        """测试二元运算"""
        code = '''
        bot "测试" {
            var a = 1 + 2 * 3
            var b = (1 + 2) * 3
            var c = 10 / 2 - 1
        }
        '''
        result = self.parser.parse(code)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.bots[0].variables), 3)
    
    def test_comparison(self):
        """测试比较运算"""
        code = '''
        bot "测试" {
            state 测试 {
                on_enter {
                    if a == b and c != d {
                        say "条件满足"
                    }
                }
            }
        }
        '''
        result = self.parser.parse(code)
        self.assertIsNotNone(result)
    
    def test_function_call_expression(self):
        """测试函数调用表达式"""
        code = '''
        bot "测试" {
            state 测试 {
                on_enter {
                    set x = length("hello")
                    set y = upper(name)
                }
            }
        }
        '''
        result = self.parser.parse(code)
        self.assertIsNotNone(result)


class TestCompleteScript(unittest.TestCase):
    """完整脚本测试"""
    
    def setUp(self):
        self.parser = BotParser()
        self.parser.build(debug=False, write_tables=False)
    
    def test_ecommerce_script(self):
        """测试电商脚本解析"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'ecommerce.bot'
        )
        
        if os.path.exists(script_path):
            with open(script_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            result = self.parser.parse(code)
            
            if self.parser.errors:
                for line, msg in self.parser.errors:
                    print(f"Error at line {line}: {msg}")
            
            self.assertIsNotNone(result)
            self.assertEqual(len(self.parser.errors), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
