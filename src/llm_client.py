"""
LLM客户端模块

集成大语言模型API，用于用户意图识别。
支持OpenAI API和兼容的API服务。
"""

import os
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IntentInfo:
    """意图信息"""
    name: str
    patterns: List[str]
    description: str
    examples: List[str]


@dataclass
class IntentResult:
    """意图识别结果"""
    intent_name: str
    confidence: float
    extracted_entities: Dict[str, str]
    reasoning: str


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo"
    ):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥，如果不提供则从环境变量获取
            base_url: API基础URL，用于兼容其他服务
            model: 使用的模型名称
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self._client = None
        
    def _get_client(self):
        """延迟初始化OpenAI客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise RuntimeError("请安装openai库: pip install openai")
            except Exception as e:
                raise RuntimeError(f"初始化OpenAI客户端失败: {e}")
        return self._client
    
    def recognize_intent(
        self,
        user_input: str,
        intents: List[IntentInfo],
        context: Optional[Dict] = None
    ) -> IntentResult:
        """
        识别用户意图
        
        Args:
            user_input: 用户输入的自然语言
            intents: 可用的意图列表
            context: 上下文信息（如当前状态、变量等）
        
        Returns:
            意图识别结果
        """
        # 构建意图描述
        intent_descriptions = []
        for intent in intents:
            desc = f"- **{intent.name}**: {intent.description}"
            if intent.patterns:
                desc += f"\n  关键词: {', '.join(intent.patterns)}"
            if intent.examples:
                desc += f"\n  示例: {', '.join(intent.examples[:3])}"
            intent_descriptions.append(desc)
        
        intents_text = "\n".join(intent_descriptions)
        intent_names = [intent.name for intent in intents]
        
        # 构建上下文描述
        context_text = ""
        if context:
            context_text = f"\n当前上下文:\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```\n"
        
        # 构建提示词
        system_prompt = """你是一个智能客服意图识别助手。你的任务是分析用户输入，识别其意图。

请按照以下JSON格式返回结果：
```json
{
    "intent": "意图名称",
    "confidence": 0.95,
    "entities": {"实体名": "实体值"},
    "reasoning": "简短的推理说明"
}
```

注意事项：
1. intent必须是给定意图列表中的一个，如果都不匹配则返回 "unknown"
2. confidence是0到1之间的置信度分数
3. entities提取用户输入中的关键实体信息（如订单号、电话号码等）
4. 只返回JSON，不要有其他内容"""

        user_prompt = f"""可用意图列表：
{intents_text}
{context_text}
用户输入: "{user_input}"

请识别用户意图。"""

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 解析JSON响应
            result = self._parse_intent_response(result_text, intent_names)
            return result
            
        except Exception as e:
            # 如果API调用失败，尝试使用本地规则匹配
            print(f"[警告] LLM API调用失败: {e}")
            return self._local_intent_match(user_input, intents)
    
    def _parse_intent_response(
        self,
        response_text: str,
        valid_intents: List[str]
    ) -> IntentResult:
        """解析LLM的意图识别响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)
            
            intent_name = result.get("intent", "unknown")
            
            # 验证意图名称
            if intent_name not in valid_intents and intent_name != "unknown":
                # 尝试模糊匹配
                for valid_intent in valid_intents:
                    if intent_name.lower() in valid_intent.lower() or \
                       valid_intent.lower() in intent_name.lower():
                        intent_name = valid_intent
                        break
                else:
                    intent_name = "unknown"
            
            return IntentResult(
                intent_name=intent_name,
                confidence=float(result.get("confidence", 0.5)),
                extracted_entities=result.get("entities", {}),
                reasoning=result.get("reasoning", "")
            )
            
        except json.JSONDecodeError:
            return IntentResult(
                intent_name="unknown",
                confidence=0.0,
                extracted_entities={},
                reasoning=f"解析响应失败: {response_text[:100]}"
            )
    
    def _local_intent_match(
        self,
        user_input: str,
        intents: List[IntentInfo]
    ) -> IntentResult:
        """本地规则匹配作为后备方案"""
        user_input_lower = user_input.lower()
        best_match = None
        best_score = 0
        
        for intent in intents:
            score = 0
            matched_patterns = []
            
            # 检查关键词匹配
            for pattern in intent.patterns:
                if pattern.lower() in user_input_lower:
                    score += 1
                    matched_patterns.append(pattern)
            
            # 检查示例相似度（简单的词重叠）
            for example in intent.examples:
                example_words = set(example.lower().split())
                input_words = set(user_input_lower.split())
                overlap = len(example_words & input_words)
                score += overlap * 0.5
            
            if score > best_score:
                best_score = score
                best_match = intent.name
        
        if best_match and best_score > 0:
            confidence = min(best_score / 5, 1.0)  # 归一化
            return IntentResult(
                intent_name=best_match,
                confidence=confidence,
                extracted_entities={},
                reasoning=f"本地规则匹配 (得分: {best_score:.2f})"
            )
        
        return IntentResult(
            intent_name="unknown",
            confidence=0.0,
            extracted_entities={},
            reasoning="无法匹配任何意图"
        )
    
    def extract_entities(
        self,
        user_input: str,
        entity_types: List[str]
    ) -> Dict[str, str]:
        """
        从用户输入中提取实体
        
        Args:
            user_input: 用户输入
            entity_types: 需要提取的实体类型列表
        
        Returns:
            实体字典
        """
        system_prompt = """你是一个实体提取助手。从用户输入中提取指定类型的实体。

返回JSON格式：
```json
{
    "实体类型1": "提取的值或null",
    "实体类型2": "提取的值或null"
}
```
只返回JSON。"""

        user_prompt = f"""需要提取的实体类型: {', '.join(entity_types)}

用户输入: "{user_input}"

请提取实体。"""

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
            
        except Exception as e:
            print(f"[警告] 实体提取失败: {e}")
            return {}


class MockLLMClient(LLMClient):
    """模拟LLM客户端，用于测试和离线使用"""
    
    def __init__(self):
        super().__init__()
        self._client = "mock"
    
    def recognize_intent(
        self,
        user_input: str,
        intents: List[IntentInfo],
        context: Optional[Dict] = None
    ) -> IntentResult:
        """使用本地规则匹配"""
        return self._local_intent_match(user_input, intents)
    
    def extract_entities(
        self,
        user_input: str,
        entity_types: List[str]
    ) -> Dict[str, str]:
        """简单的正则实体提取"""
        entities = {}
        
        # 订单号：10-20位数字
        order_match = re.search(r'\b(\d{10,20})\b', user_input)
        if order_match and 'order_id' in entity_types:
            entities['order_id'] = order_match.group(1)
        
        # 手机号
        phone_match = re.search(r'\b(1[3-9]\d{9})\b', user_input)
        if phone_match and 'phone' in entity_types:
            entities['phone'] = phone_match.group(1)
        
        # 金额
        amount_match = re.search(r'(\d+(?:\.\d{1,2})?)\s*[元块]', user_input)
        if amount_match and 'amount' in entity_types:
            entities['amount'] = amount_match.group(1)
        
        return entities


def create_llm_client(
    use_mock: bool = False,
    **kwargs
) -> LLMClient:
    """
    创建LLM客户端
    
    Args:
        use_mock: 是否使用模拟客户端
        **kwargs: 传递给LLMClient的参数
    
    Returns:
        LLM客户端实例
    """
    if use_mock:
        return MockLLMClient()
    
    # 检查API密钥
    api_key = kwargs.get('api_key') or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[警告] 未配置OPENAI_API_KEY，使用模拟客户端")
        return MockLLMClient()
    
    return LLMClient(**kwargs)


# 测试代码
if __name__ == '__main__':
    # 测试意图
    test_intents = [
        IntentInfo(
            name="查询订单",
            patterns=["订单", "物流", "快递", "发货", "到货"],
            description="用户想要查询订单状态或物流信息",
            examples=["我的订单到哪了", "查一下物流"]
        ),
        IntentInfo(
            name="退货退款",
            patterns=["退货", "退款", "退钱", "换货"],
            description="用户想要退货或退款",
            examples=["我要退货", "怎么申请退款"]
        ),
        IntentInfo(
            name="问候",
            patterns=["你好", "hi", "hello", "在吗"],
            description="用户打招呼",
            examples=["你好", "在吗"]
        )
    ]
    
    # 使用模拟客户端测试
    client = create_llm_client(use_mock=True)
    
    test_inputs = [
        "你好，我想查一下订单",
        "我的快递到哪了，订单号是1234567890123",
        "这个东西不好用，我要退货",
        "今天天气怎么样"
    ]
    
    print("意图识别测试：")
    print("=" * 50)
    
    for user_input in test_inputs:
        result = client.recognize_intent(user_input, test_intents)
        print(f"\n用户输入: {user_input}")
        print(f"识别意图: {result.intent_name}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"提取实体: {result.extracted_entities}")
        print(f"推理: {result.reasoning}")
