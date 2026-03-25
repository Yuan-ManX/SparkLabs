# SparkLabs Python-C++ 混合架构文档

## 概述

SparkLabs 采用了先进的 **C++/Python 混合架构**，充分利用两种语言的优势：

- **C++ 层**：高性能核心引擎（数学、场景、渲染、资源管理）
- **Python 层**：AI/ML 集成、快速原型开发、外部 API 连接
- **PyBind11 桥接层**：两层之间的无缝通信

## 架构设计

### 层次结构

```
┌─────────────────────────────────────────────────────────┐
│                   Python 应用层                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  AI服务集成   │  │  游戏逻辑    │  │  快速原型    │  │
│  │ (OpenAI等)   │  │  (Python)    │  │  开发环境    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              PyBind11 绑定层                            │
│         (C++ ↔ Python 无缝通信)                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   C++ 核心层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  数学库      │  │  场景系统    │  │  渲染系统    │  │
│  │ (高性能)     │  │ (GameObject)  │  │ (GPU加速)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  内存管理    │  │  资源管理    │  │  物理引擎    │  │
│  │ (SmartPtr)   │  │ (异步加载)   │  │ (可选)       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
SparkLabs/
├── core/                    # C++ 核心模块
│   ├── math/               # 数学库
│   ├── memory/             # 内存管理
│   ├── object/             # 对象系统
│   └── ...
├── engine/                 # C++ 引擎模块
│   ├── scene/              # 场景系统
│   ├── resource/           # 资源管理
│   └── Engine.h/cpp        # 主引擎类
├── sparkai/               # AI 模块 (C++)
├── scripts/               # Python 集成
│   ├── bindings/          # PyBind11 绑定
│   └── python/            # Python 模块
│       ├── __init__.py
│       ├── ai_integration.py  # AI 服务集成
│       ├── game_loop.py       # 游戏循环集成
│       └── example_game.py    # 示例游戏
└── ...
```

## 核心功能

### 1. C++ 引擎类 (Engine)

位置：`engine/Engine.h` 和 `engine/Engine.cpp`

**功能：**
- 单例模式的引擎入口
- 跨平台的高精度计时器
- 完整的主循环（Update、Render）
- 场景管理

**使用示例：**
```cpp
#include "engine/Engine.h"

int main() {
    SparkLabs::Engine* engine = SparkLabs::Engine::GetInstance();
    engine->Initialize();
    
    SparkLabs::Scene* scene = new SparkLabs::Scene();
    engine->SetScene(scene);
    
    engine->Run();  // 启动主循环
    engine->Shutdown();
    return 0;
}
```

### 2. Python 游戏系统 (PythonGameSystem)

位置：`scripts/python/game_loop.py`

**功能：**
- 可扩展的 Python 游戏系统基类
- 与 C++ 引擎同步的更新钩子
- AI 决策系统集成

**使用示例：**
```python
from game_loop import PythonGameSystem, register_system

class MyGameSystem(PythonGameSystem):
    def __init__(self):
        super().__init__("MySystem")
    
    def update(self, delta_time: float):
        # 每帧执行的逻辑
        pass

register_system(MyGameSystem())
```

### 3. AI 服务集成 (AIService)

位置：`scripts/python/ai_integration.py`

**支持的服务：**
- **OpenAI**: GPT-4、文本生成、对话
- **HuggingFace**: 本地模型推理
- **LocalModel**: ONNX 本地模型

**使用示例：**
```python
from ai_integration import (
    OpenAIService,
    AIServiceManager,
    get_ai_manager
)

manager = get_ai_manager()
service = OpenAIService(api_key="your-key", model="gpt-4")
await manager.register_service("openai", service)

result = await manager.process("openai", {
    "prompt": "Hello, world!",
    "max_tokens": 100
})
```

## 构建指南

### 1. 构建 C++ 引擎

```bash
mkdir build && cd build
cmake ..
cmake --build . --config Release
```

### 2. 构建 Python 绑定

```bash
cd build
cmake .. -DSPARKLABS_PYTHON_BINDINGS=ON
cmake --build . --config Release
```

### 3. Python 环境设置

```bash
# 安装依赖
pip install pybind11
pip install openai transformers onnxruntime  # 可选，用于AI服务
```

## Python 快速开始

### 基础使用

```python
import sys
sys.path.insert(0, 'build/python')

import sparklabs

# 初始化引擎
engine = sparklabs.Engine.GetInstance()
engine.Initialize()

# 创建场景和对象
scene = sparklabs.Scene()
scene.SetName("MyScene")
engine.SetScene(scene)

player = scene.CreateEntity("Player")
player.SetPosition(sparklabs.Vector3(0, 1, 0))

# 运行引擎
# engine.Run()  # 取消注释以启动

# 清理
engine.Shutdown()
```

### 高级：Python 游戏系统

```python
from game_loop import (
    PythonGameSystem,
    register_system,
    get_game_loop
)

class AIDecisionSystem(PythonGameSystem):
    def __init__(self):
        super().__init__("AIDecision")
        self.npcs = []
    
    def update(self, delta_time):
        for npc in self.npcs:
            self._make_decision(npc)

# 注册系统
ai_system = AIDecisionSystem()
register_system(ai_system)

# 在引擎循环中更新
game_loop = get_game_loop()
game_loop.initialize(engine)
game_loop.update(delta_time)
```

## 核心优势

### 1. 性能与灵活性的完美平衡
- **C++**: 数学计算、场景遍历、渲染 - 极致性能
- **Python**: AI 逻辑、游戏玩法、外部 API - 快速开发

### 2. 无缝的类型转换
通过 PyBind11，C++ 和 Python 类型自动转换：
- `Vector3` ↔ `tuple` 或自定义 Python 类
- `String` ↔ `str`
- `Variant` ↔ 任意 Python 对象

### 3. 可扩展架构
- 新增 C++ 系统只需添加到引擎
- 新增 Python 系统只需继承 `PythonGameSystem`
- AI 服务可通过 `AIService` 抽象轻松添加

## 最佳实践

### 1. 职责分离
- **C++**: 处理每帧数百万次的操作
- **Python**: 处理每秒几次的决策和 AI 逻辑

### 2. 数据传递
- 最小化 C++ ↔ Python 数据传递频率
- 批量传递数据而非单条
- 使用共享内存或缓冲区处理大数据

### 3. 错误处理
- C++ 异常通过 PyBind11 自动转换为 Python 异常
- 在 Python 侧使用 try/except 处理 AI 服务错误

## 未来扩展

### 计划中的功能
- [ ] 更多 AI 服务集成（Claude、Stable Diffusion 等）
- [ ] 热重载 Python 代码
- [ ] Python 脚本调试支持
- [ ] 性能分析工具
- [ ] 更多示例和教程

## 总结

SparkLabs 的 Python-C++ 混合架构提供了：
1. **最佳性能**: C++ 处理核心引擎
2. **最大灵活性**: Python 处理 AI 和游戏逻辑
3. **无缝集成**: PyBind11 实现两层通信
4. **易于扩展**: 模块化设计支持快速添加新功能

这种架构特别适合 AI 原生游戏引擎，能够充分利用 Python 丰富的 AI/ML 生态系统，同时保持 C++ 的高性能特性。
