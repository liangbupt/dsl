"""
解释器测试模块
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from src.parser import BotParser
from src.interpreter import Interpreter, IOHandler, Environment
from src.llm_client import MockLLMClient


class MockIO:
    """模拟I/O处理器"""
    
    def __init__(self):
        self.outputs = []
        self.input_queue = []
    
    def say(self, message):
        self.outputs.append(message)
    
    def ask(self, prompt):
        self.outputs.append(prompt)
        if self.input_queue:
            return self.input_queue.pop(0)
        return ""
    
    def set_inputs(self, inputs):
        self.input_queue = list(inputs)
    
    def clear(self):
        self.outputs = []
        self.input_queue = []


class TestEnvironment(unittest.TestCase):
    """环境测试"""
    
    def test_variable_operations(self):
        """测试变量操作"""
        env = Environment()
        env.define('x', 10)
        self.assertEqual(env.get('x'), 10)
        
        env.set('x', 20)
        self.assertEqual(env.get('x'), 20)
    
    def test_nested_environment(self):
        """测试嵌套环境"""
        parent = Environment()
        parent.define('x', 10)
        
        child = Environment(parent=parent)
        child.define('y', 20)
        
        self.assertEqual(child.get('x'), 10)
        self.assertEqual(child.get('y'), 20)
        
        # 修改父环境的变量
        child.set('x', 30)
        self.assertEqual(parent.get('x'), 30)
    
    def test_undefined_variable(self):
        """测试未定义变量"""
        env = Environment()
        with self.assertRaises(NameError):
            env.get('undefined')


class TestInterpreter(unittest.TestCase):
    """解释器测试"""
    
    def setUp(self):
        self.parser = BotParser()
        self.parser.build(debug=False, write_tables=False)
        self.mock_io = MockIO()
        self.io_handler = IOHandler(
            output_callback=self.mock_io.say,
            input_callback=self.mock_io.ask
        )
    
    def parse_and_run(self, code):
        """解析并运行代码"""
        program = self.parser.parse(code)
        self.assertIsNotNone(program, f"解析失败: {self.parser.errors}")
        
        interpreter = Interpreter(
            io_handler=self.io_handler,
            llm_client=MockLLMClient()
        )
        interpreter.load_program(program)
        interpreter.start()
        return interpreter
    
    def test_simple_say(self):
        """测试say语句"""
        code = '''
        bot "测试" {
            state 初始 initial {
                on_enter {
                    say "你好世界"
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("你好世界", self.mock_io.outputs)
    
    def test_variable_usage(self):
        """测试变量使用"""
        code = '''
        bot "测试" {
            var name = "张三"
            state 初始 initial {
                on_enter {
                    say "你好 " + name
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("你好 张三", self.mock_io.outputs)
    
    def test_arithmetic(self):
        """测试算术运算"""
        code = '''
        bot "测试" {
            var x = 10
            var y = 3
            state 初始 initial {
                on_enter {
                    say str(x + y)
                    say str(x - y)
                    say str(x * y)
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("13", self.mock_io.outputs)
        self.assertIn("7", self.mock_io.outputs)
        self.assertIn("30", self.mock_io.outputs)
    
    def test_if_statement(self):
        """测试if语句"""
        code = '''
        bot "测试" {
            var x = 5
            state 初始 initial {
                on_enter {
                    if x > 0 {
                        say "正数"
                    } else {
                        say "非正数"
                    }
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("正数", self.mock_io.outputs)
    
    def test_builtin_functions(self):
        """测试内置函数"""
        code = '''
        bot "测试" {
            var s = "hello"
            state 初始 initial {
                on_enter {
                    say str(length(s))
                    say upper(s)
                    say lower("WORLD")
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("5", self.mock_io.outputs)
        self.assertIn("HELLO", self.mock_io.outputs)
        self.assertIn("world", self.mock_io.outputs)
    
    def test_user_function(self):
        """测试用户自定义函数"""
        code = '''
        bot "测试" {
            func double(n) {
                return n * 2
            }
            
            state 初始 initial {
                on_enter {
                    set result = double(5)
                    say str(result)
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("10", self.mock_io.outputs)
    
    def test_intent_matching(self):
        """测试意图匹配"""
        code = '''
        bot "测试" {
            intent 问候 {
                patterns: ["你好", "hi"]
                description: "问候"
            }
            
            state 初始 initial {
                on_enter {
                    say "欢迎"
                }
                when 问候 -> 问候状态
                fallback {
                    say "不理解"
                }
            }
            
            state 问候状态 {
                on_enter {
                    say "你好呀"
                }
            }
        }
        '''
        interpreter = self.parse_and_run(code)
        self.mock_io.clear()
        
        # 测试意图匹配 - response包含了输出
        response, _ = interpreter.process_input("你好")
        # 检查response或者mock_io.outputs
        self.assertTrue("你好呀" in response or "你好呀" in self.mock_io.outputs,
                        f"Expected '你好呀' in response='{response}' or outputs={self.mock_io.outputs}")
    
    def test_state_transition(self):
        """测试状态转换"""
        code = '''
        bot "测试" {
            intent 下一步 {
                patterns: ["继续", "下一步"]
                description: "继续"
            }
            
            state 状态1 initial {
                on_enter {
                    say "状态1"
                }
                when 下一步 -> 状态2
            }
            
            state 状态2 {
                on_enter {
                    say "状态2"
                }
                when 下一步 -> 状态3
            }
            
            state 状态3 final {
                on_enter {
                    say "结束"
                }
            }
        }
        '''
        interpreter = self.parse_and_run(code)
        self.assertIn("状态1", self.mock_io.outputs)
        
        self.mock_io.clear()
        response1, _ = interpreter.process_input("继续")
        self.assertTrue("状态2" in response1 or "状态2" in self.mock_io.outputs,
                        f"Expected '状态2' in response='{response1}' or outputs={self.mock_io.outputs}")
        
        self.mock_io.clear()
        response2, _ = interpreter.process_input("下一步")
        self.assertTrue("结束" in response2 or "结束" in self.mock_io.outputs,
                        f"Expected '结束' in response='{response2}' or outputs={self.mock_io.outputs}")
    
    def test_list_operations(self):
        """测试列表操作"""
        code = '''
        bot "测试" {
            var items = [1, 2, 3]
            state 初始 initial {
                on_enter {
                    say str(length(items))
                    say str(first(items))
                    say str(last(items))
                }
            }
        }
        '''
        self.parse_and_run(code)
        self.assertIn("3", self.mock_io.outputs)
        self.assertIn("1", self.mock_io.outputs)


class TestLLMIntegration(unittest.TestCase):
    """LLM集成测试"""
    
    def test_mock_intent_recognition(self):
        """测试模拟意图识别"""
        from src.llm_client import MockLLMClient, IntentInfo
        
        client = MockLLMClient()
        
        intents = [
            IntentInfo(
                name="查询订单",
                patterns=["订单", "物流"],
                description="查询订单",
                examples=[]
            ),
            IntentInfo(
                name="问候",
                patterns=["你好", "hi"],
                description="问候",
                examples=[]
            )
        ]
        
        # 测试订单意图
        result = client.recognize_intent("我想查一下订单", intents)
        self.assertEqual(result.intent_name, "查询订单")
        
        # 测试问候意图
        result = client.recognize_intent("你好呀", intents)
        self.assertEqual(result.intent_name, "问候")
        
        # 测试未知意图
        result = client.recognize_intent("今天天气怎么样", intents)
        self.assertEqual(result.intent_name, "unknown")


if __name__ == '__main__':
    unittest.main(verbosity=2)
