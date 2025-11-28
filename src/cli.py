"""
命令行界面模块

提供交互式命令行界面，运行客服机器人脚本。
"""

import os
import sys
import argparse
from typing import Optional

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from colorama import init, Fore, Style
    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = CYAN = YELLOW = RED = MAGENTA = BLUE = ''
        RESET = ''
    class Style:
        BRIGHT = DIM = RESET_ALL = ''


class ColorPrinter:
    """彩色输出工具"""
    
    @staticmethod
    def bot(message: str):
        """机器人消息"""
        if HAS_COLOR:
            print(f"{Fore.CYAN}{message}{Style.RESET_ALL}")
        else:
            print(f"[机器人] {message}")
    
    @staticmethod
    def user(message: str):
        """用户消息"""
        if HAS_COLOR:
            print(f"{Fore.GREEN}>>> {message}{Style.RESET_ALL}")
        else:
            print(f"[用户] >>> {message}")
    
    @staticmethod
    def system(message: str):
        """系统消息"""
        if HAS_COLOR:
            print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
        else:
            print(f"[系统] {message}")
    
    @staticmethod
    def error(message: str):
        """错误消息"""
        if HAS_COLOR:
            print(f"{Fore.RED}[错误] {message}{Style.RESET_ALL}")
        else:
            print(f"[错误] {message}")
    
    @staticmethod
    def debug(message: str):
        """调试消息"""
        if HAS_COLOR:
            print(f"{Fore.MAGENTA}[调试] {message}{Style.RESET_ALL}")
        else:
            print(f"[调试] {message}")


class CLI:
    """命令行界面"""
    
    def __init__(self, script_path: str, use_llm: bool = False, debug: bool = False):
        """
        初始化CLI
        
        Args:
            script_path: 脚本文件路径
            use_llm: 是否使用真实LLM API
            debug: 是否启用调试模式
        """
        self.script_path = script_path
        self.use_llm = use_llm
        self.debug = debug
        self.printer = ColorPrinter()
        self.interpreter = None
        
    def load_script(self) -> bool:
        """加载脚本文件"""
        try:
            # 延迟导入，避免循环依赖
            from src.parser import BotParser
            from src.interpreter import Interpreter, IOHandler
            from src.llm_client import create_llm_client
            
            # 读取脚本文件
            with open(self.script_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # 解析脚本
            parser = BotParser()
            parser.build(debug=False, write_tables=False)
            program = parser.parse(source)
            
            if parser.errors:
                self.printer.error("脚本解析失败：")
                for line, msg in parser.errors:
                    self.printer.error(f"  第{line}行: {msg}")
                return False
            
            if not program:
                self.printer.error("脚本解析失败：未能生成AST")
                return False
            
            # 创建LLM客户端
            llm_client = create_llm_client(use_mock=not self.use_llm)
            
            # 创建I/O处理器
            io_handler = IOHandler(
                output_callback=self.printer.bot,
                input_callback=self._get_input
            )
            
            # 创建解释器
            self.interpreter = Interpreter(
                io_handler=io_handler,
                llm_client=llm_client
            )
            
            # 加载程序
            self.interpreter.load_program(program)
            
            return True
            
        except FileNotFoundError:
            self.printer.error(f"找不到脚本文件: {self.script_path}")
            return False
        except Exception as e:
            self.printer.error(f"加载脚本失败: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _get_input(self, prompt: str) -> str:
        """获取用户输入"""
        self.printer.bot(prompt)
        try:
            user_input = input(f"{Fore.GREEN}>>> " if HAS_COLOR else ">>> ")
            if HAS_COLOR:
                print(Style.RESET_ALL, end='')
            return user_input.strip()
        except (EOFError, KeyboardInterrupt):
            return "退出"
    
    def run(self):
        """运行交互式会话"""
        self.printer.system("=" * 50)
        self.printer.system("智能客服机器人 DSL 解释器")
        self.printer.system("=" * 50)
        self.printer.system(f"加载脚本: {self.script_path}")
        
        if not self.load_script():
            return
        
        self.printer.system("脚本加载成功！")
        self.printer.system("输入 'quit' 或 'exit' 退出，'help' 查看帮助")
        self.printer.system("=" * 50)
        print()
        
        # 启动机器人
        self.interpreter.start()
        
        # 主循环
        while True:
            try:
                # 获取用户输入
                user_input = input(f"{Fore.GREEN}>>> " if HAS_COLOR else ">>> ")
                if HAS_COLOR:
                    print(Style.RESET_ALL, end='')
                
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    self.printer.system("再见！")
                    break
                
                if user_input.lower() in ['help', '帮助', 'h', '?']:
                    self._show_help()
                    continue
                
                if user_input.lower() in ['state', '状态']:
                    self._show_state()
                    continue
                
                if user_input.lower() in ['vars', '变量']:
                    self._show_vars()
                    continue
                
                if user_input.lower() in ['reload', '重载']:
                    self.printer.system("重新加载脚本...")
                    if self.load_script():
                        self.interpreter.start()
                    continue
                
                # 处理用户输入
                print()  # 空行分隔
                
                if self.debug:
                    self.printer.debug(f"用户输入: {user_input}")
                    self.printer.debug(f"当前状态: {self.interpreter.current_state.name if self.interpreter.current_state else 'None'}")
                
                response, continue_chat = self.interpreter.process_input(user_input)
                
                if self.debug:
                    intent = self.interpreter.env.get('_intent') if self.interpreter.env else 'unknown'
                    confidence = self.interpreter.env.get('_confidence') if self.interpreter.env else 0
                    self.printer.debug(f"识别意图: {intent} (置信度: {confidence:.2f})")
                
                print()  # 空行分隔
                
                if not continue_chat:
                    self.printer.system("对话结束")
                    break
                
            except KeyboardInterrupt:
                print()
                self.printer.system("收到中断信号，退出...")
                break
            except Exception as e:
                self.printer.error(f"执行错误: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
    
    def _show_help(self):
        """显示帮助信息"""
        print()
        self.printer.system("可用命令：")
        self.printer.system("  quit, exit, q - 退出程序")
        self.printer.system("  help, h, ?    - 显示此帮助")
        self.printer.system("  state         - 显示当前状态")
        self.printer.system("  vars          - 显示变量值")
        self.printer.system("  reload        - 重新加载脚本")
        print()
    
    def _show_state(self):
        """显示当前状态"""
        print()
        if self.interpreter and self.interpreter.current_state:
            state = self.interpreter.current_state
            self.printer.system(f"当前状态: {state.name}")
            self.printer.system(f"是否初始: {state.is_initial}")
            self.printer.system(f"是否结束: {state.is_final}")
            if state.transitions:
                self.printer.system("可用转换:")
                for t in state.transitions:
                    self.printer.system(f"  {t.intent_name} -> {t.target_state}")
        else:
            self.printer.system("未加载状态")
        print()
    
    def _show_vars(self):
        """显示变量值"""
        print()
        if self.interpreter and self.interpreter.env:
            self.printer.system("变量值：")
            for name, value in self.interpreter.env.variables.items():
                if not name.startswith('_'):
                    self.printer.system(f"  {name} = {repr(value)}")
        else:
            self.printer.system("未加载环境")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='智能客服机器人 DSL 解释器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python cli.py scripts/ecommerce.bot      运行电商客服
  python cli.py scripts/banking.bot        运行银行客服
  python cli.py scripts/telecom.bot        运行电信客服
  python cli.py script.bot --llm           使用真实LLM API
  python cli.py script.bot --debug         启用调试模式
        '''
    )
    
    parser.add_argument(
        'script',
        help='DSL脚本文件路径 (.bot文件)'
    )
    
    parser.add_argument(
        '--llm',
        action='store_true',
        help='使用真实LLM API进行意图识别（需要配置OPENAI_API_KEY）'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='启用调试模式，显示详细信息'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='DSL Interpreter v1.0.0'
    )
    
    args = parser.parse_args()
    
    # 检查脚本文件
    if not os.path.exists(args.script):
        print(f"错误: 找不到脚本文件 '{args.script}'")
        sys.exit(1)
    
    # 运行CLI
    cli = CLI(
        script_path=args.script,
        use_llm=args.llm,
        debug=args.debug
    )
    cli.run()


if __name__ == '__main__':
    main()
