# DSL语法规范文档

## 1. 概述

本DSL（Domain Specific Language）是专门为智能客服机器人设计的脚本语言。它采用状态机模型来描述对话流程，通过意图识别驱动状态转换，实现灵活的客服对话逻辑。

## 2. 语法结构

### 2.1 程序结构

一个DSL程序由一个或多个`bot`定义组成：

```
bot "机器人名称" {
    # 意图定义
    intent 意图名 { ... }
    
    # 状态定义
    state 状态名 { ... }
    
    # 变量定义
    var 变量名 = 初始值
    
    # 函数定义
    func 函数名(参数列表) { ... }
}
```

### 2.2 注释

使用 `#` 开始单行注释：

```
# 这是一行注释
bot "测试" {  # 行尾注释
    ...
}
```

## 3. 意图定义 (Intent)

意图定义了用户可能表达的意图，用于触发状态转换。

### 语法

```
intent 意图名称 {
    patterns: ["关键词1", "关键词2", ...]
    description: "意图描述"
    examples: ["示例句子1", "示例句子2", ...]
}
```

### 属性说明

| 属性 | 类型 | 必填 | 描述 |
|------|------|------|------|
| patterns | 字符串列表 | 是 | 用于匹配的关键词列表 |
| description | 字符串 | 否 | 意图的自然语言描述，供LLM理解 |
| examples | 字符串列表 | 否 | 用户输入示例，提高识别准确率 |

### 示例

```
intent 查询订单 {
    patterns: ["订单", "物流", "快递", "发货"]
    description: "用户想要查询订单状态或物流信息"
    examples: ["我的订单到哪了", "帮我查一下物流"]
}
```

## 4. 状态定义 (State)

状态定义了对话的不同阶段，包括进入/退出动作、转换规则和兜底处理。

### 语法

```
state 状态名称 [修饰符] {
    on_enter { ... }      # 进入状态时执行
    on_exit { ... }       # 退出状态时执行
    on_message { ... }    # 收到消息时执行
    
    when 意图名 -> 目标状态 [if 条件]
    
    fallback { ... }      # 意图未匹配时执行
}
```

### 修饰符

| 修饰符 | 描述 |
|--------|------|
| initial | 标记为初始状态，机器人启动时进入此状态 |
| final | 标记为结束状态，进入后对话结束 |

### 示例

```
state 欢迎状态 initial {
    on_enter {
        say "您好！欢迎使用智能客服。"
    }
    
    when 查询订单 -> 订单查询
    when 退货退款 -> 退款处理
    
    fallback {
        say "抱歉，我没有理解您的意思。"
    }
}

state 结束状态 final {
    on_enter {
        say "感谢使用，再见！"
    }
}
```

## 5. 变量定义 (Variable)

### 语法

```
var 变量名 = 初始值
var 变量名            # 初始值为null
```

### 支持的数据类型

- **字符串**: `"hello"` 或 `'world'`
- **数字**: `42` 或 `3.14`
- **布尔值**: `true` 或 `false`
- **空值**: `null`
- **列表**: `[1, 2, 3]` 或 `["a", "b"]`

### 示例

```
var order_id = ""
var count = 0
var is_vip = false
var items = []
```

## 6. 函数定义 (Function)

### 语法

```
func 函数名(参数1, 参数2, ...) {
    # 函数体
    return 返回值
}
```

### 参数默认值

```
func greet(name = "用户") {
    say "你好，" + name
}
```

### 示例

```
func validate_phone(phone) {
    if length(phone) == 11 {
        return true
    }
    return false
}
```

## 7. 语句类型

### 7.1 say语句

输出消息给用户：

```
say "欢迎光临！"
say "您的订单号是：" + order_id
```

### 7.2 ask语句

向用户提问并将回答存入变量：

```
ask "请输入您的手机号：" -> phone
ask "请问需要什么帮助？" -> request
```

### 7.3 set语句

设置变量值：

```
set count = count + 1
set name = "张三"
set result = validate_phone(phone)
```

### 7.4 goto语句

跳转到指定状态：

```
goto 订单查询
goto 结束状态
```

### 7.5 call语句

调用函数（不使用返回值）：

```
call send_notification(user_id, message)
call log("用户查询了订单")
```

### 7.6 return语句

从函数返回：

```
return true
return result
return      # 返回null
```

### 7.7 if语句

条件分支：

```
if condition {
    # 条件为真时执行
} elif other_condition {
    # 其他条件
} else {
    # 默认执行
}
```

### 7.8 while语句

循环：

```
while count < 10 {
    set count = count + 1
}
```

### 7.9 for语句

遍历：

```
for item in items {
    say item
}

for i in [1, 2, 3] {
    say str(i)
}
```

## 8. 表达式

### 8.1 算术运算符

| 运算符 | 描述 | 示例 |
|--------|------|------|
| + | 加法/字符串连接 | `1 + 2`, `"a" + "b"` |
| - | 减法 | `5 - 3` |
| * | 乘法 | `2 * 3` |
| / | 除法 | `10 / 2` |
| % | 取模 | `7 % 3` |

### 8.2 比较运算符

| 运算符 | 描述 | 示例 |
|--------|------|------|
| == | 等于 | `a == b` |
| != | 不等于 | `a != b` |
| < | 小于 | `a < b` |
| > | 大于 | `a > b` |
| <= | 小于等于 | `a <= b` |
| >= | 大于等于 | `a >= b` |

### 8.3 逻辑运算符

| 运算符 | 描述 | 示例 |
|--------|------|------|
| and | 逻辑与 | `a and b` |
| or | 逻辑或 | `a or b` |
| not | 逻辑非 | `not a` |

### 8.4 优先级（从高到低）

1. 括号 `()`
2. 一元运算符 `-`, `not`
3. 乘除取模 `*`, `/`, `%`
4. 加减 `+`, `-`
5. 比较 `<`, `>`, `<=`, `>=`
6. 相等 `==`, `!=`
7. 逻辑与 `and`
8. 逻辑或 `or`

## 9. 内置函数

### 9.1 字符串函数

| 函数 | 描述 | 示例 |
|------|------|------|
| `length(s)` | 返回字符串长度 | `length("hello")` → `5` |
| `upper(s)` | 转换为大写 | `upper("hello")` → `"HELLO"` |
| `lower(s)` | 转换为小写 | `lower("HELLO")` → `"hello"` |
| `trim(s)` | 去除首尾空白 | `trim("  hi  ")` → `"hi"` |
| `contains(s, sub)` | 检查是否包含子串 | `contains("hello", "ll")` → `true` |
| `startswith(s, pre)` | 检查前缀 | `startswith("hello", "he")` → `true` |
| `endswith(s, suf)` | 检查后缀 | `endswith("hello", "lo")` → `true` |
| `replace(s, old, new)` | 替换子串 | `replace("hello", "l", "L")` → `"heLLo"` |
| `split(s, sep)` | 分割字符串 | `split("a,b,c", ",")` → `["a","b","c"]` |
| `join(list, sep)` | 连接列表 | `join(["a","b"], "-")` → `"a-b"` |

### 9.2 类型转换函数

| 函数 | 描述 | 示例 |
|------|------|------|
| `str(x)` | 转换为字符串 | `str(42)` → `"42"` |
| `int(x)` | 转换为整数 | `int("42")` → `42` |
| `float(x)` | 转换为浮点数 | `float("3.14")` → `3.14` |
| `bool(x)` | 转换为布尔值 | `bool(1)` → `true` |

### 9.3 列表函数

| 函数 | 描述 | 示例 |
|------|------|------|
| `length(list)` | 返回列表长度 | `length([1,2,3])` → `3` |
| `first(list)` | 返回第一个元素 | `first([1,2,3])` → `1` |
| `last(list)` | 返回最后一个元素 | `last([1,2,3])` → `3` |
| `append(list, item)` | 添加元素 | `append([1,2], 3)` → `[1,2,3]` |
| `pop(list)` | 移除并返回最后元素 | `pop([1,2,3])` → `3` |
| `slice(list, start, end)` | 切片 | `slice([1,2,3,4], 1, 3)` → `[2,3]` |

### 9.4 数学函数

| 函数 | 描述 | 示例 |
|------|------|------|
| `abs(x)` | 绝对值 | `abs(-5)` → `5` |
| `min(a, b)` | 最小值 | `min(3, 5)` → `3` |
| `max(a, b)` | 最大值 | `max(3, 5)` → `5` |
| `round(x)` | 四舍五入 | `round(3.7)` → `4` |

### 9.5 实用函数

| 函数 | 描述 | 示例 |
|------|------|------|
| `print(...)` | 输出信息（调试用） | `print("debug:", x)` |
| `format(template, ...)` | 格式化字符串 | `format("你好{}", name)` |
| `match(pattern, s)` | 正则匹配 | `match("\\d+", "123")` → `true` |
| `current_state()` | 获取当前状态名 | `current_state()` → `"欢迎状态"` |

## 10. 特殊变量

在状态处理中可以访问以下特殊变量：

| 变量 | 描述 |
|------|------|
| `_user_input` | 当前用户输入的原始文本 |
| `_intent` | 识别出的意图名称 |
| `_confidence` | 意图识别的置信度（0-1） |
| `_entities` | 提取的实体字典 |

## 11. 完整示例

```
# 简单问答机器人示例

bot "问答助手" {
    # 意图定义
    intent 问候 {
        patterns: ["你好", "hi", "hello"]
        description: "用户打招呼"
    }
    
    intent 询问天气 {
        patterns: ["天气", "下雨", "温度"]
        description: "用户询问天气"
    }
    
    intent 告别 {
        patterns: ["再见", "拜拜", "bye"]
        description: "用户告别"
    }
    
    # 变量
    var user_name = ""
    var ask_count = 0
    
    # 函数
    func increment_count() {
        set ask_count = ask_count + 1
    }
    
    # 状态定义
    state 欢迎 initial {
        on_enter {
            say "你好！我是问答助手。"
            ask "请问怎么称呼您？" -> user_name
            say "很高兴认识你，" + user_name + "！"
        }
        
        when 询问天气 -> 天气查询
        when 告别 -> 结束
        
        fallback {
            say "抱歉，我没听懂。"
            say "你可以问我天气，或者说再见结束对话。"
        }
    }
    
    state 天气查询 {
        on_enter {
            call increment_count()
            say "正在查询天气..."
            say "今天天气晴朗，气温25°C，适合出行！"
            say "你已经问了 " + str(ask_count) + " 次天气了。"
            goto 欢迎
        }
    }
    
    state 结束 final {
        on_enter {
            say "再见，" + user_name + "！下次再聊！"
        }
    }
}
```

## 12. 最佳实践

1. **合理划分状态**：每个状态应该代表对话的一个明确阶段
2. **定义充分的意图**：包含足够的patterns和examples提高识别率
3. **提供fallback处理**：每个状态都应该有兜底响应
4. **使用有意义的命名**：变量和函数名应该清晰表达其用途
5. **添加注释**：在复杂逻辑处添加注释说明
6. **验证用户输入**：使用条件判断验证用户输入的有效性
