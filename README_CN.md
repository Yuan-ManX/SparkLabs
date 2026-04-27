<div align="center">

<img src="./assets/SparkLabs-Logo.png" alt="SparkLabs Logo"/>

# Spark Labs

### AI 原生游戏引擎 💥
### 点燃你的无限游戏 🎮

![版本](https://img.shields.io/badge/version-2.0.0-blue)
![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-3178C6)
![许可证](https://img.shields.io/badge/license-MIT-green)
![Stars](https://img.shields.io/github/stars/Yuan-ManX/SparkLabs?style=social)


### [English](./README.md) | [中文文档](./README_CN.md)

</div>


## 概述

**SparkLabs** 是一款新一代的AI原生游戏引擎，将人工智能能力深度融入游戏开发的核心架构中。传统游戏引擎依赖手工编码的游戏逻辑和预定义的资源管道，而 SparkLabs 通过AI驱动的程序化内容生成、智能NPC行为系统、自适应渲染和动态难度调整，彻底革新游戏开发范式。

引擎采用三层架构设计：C++高性能游戏引擎核心、AI Agent基础层（sparkai）、Web可视化编辑器——从引擎到编辑器打造无缝的AI原生开发体验。

AI Agent基础层（sparkai）提供了完整的多Agent编排系统、分层记忆、工具注册表和LLM提供商集成——所有功能均从零开始为AI原生游戏开发而设计。Web可视化编辑器提供了直观的场景设计、工作流编排、NPC创建和叙事编辑界面。

## 核心特性

### AI原生Agent基础层
- 基于Python的SparkAgent，支持观察-思考-行动循环
- 多提供商LLM集成（OpenAI、Anthropic、DeepSeek、Ollama、本地模型）
- 分层记忆系统（短期、长期、情景、语义、工作记忆）
- 工具注册表，内置游戏开发引擎工具
- 多Agent编排，自动能力匹配

### AI原生架构
- AI推理能力深度集成到核心引擎架构
- AI驱动的对象系统和事件处理机制
- 支持神经网络模型（ONNX Runtime集成）
- C++17核心引擎与Python AI层通过PyBind11桥接

### 神经渲染管线
- 实时AI超分辨率（神经上采样）
- AI环境光遮蔽（N/AO）
- 智能抗锯齿（Neural AA）
- 基于场景理解的自适应渲染

### 智能NPC系统
- 神经网络驱动的NPC决策，双网络架构
- 10维人格特质系统
- 7种情感类型的情绪状态机
- 短期、长期、情景、语义四层记忆系统
- 注意力机制，焦点管理
- 行为树系统，支持选择器、序列、装饰器、并行节点
- 上下文感知的对话生成

### 自适应游戏玩法
- 玩家技能追踪和建模
- 实时动态难度调整
- 参与度指标监控
- 个性化玩家体验优化

### AI叙事引擎
- 分支故事图，支持变量追踪和条件逻辑
- 程序化任务生成，6+模板类型
- 动态任务定制，上下文感知文本
- 故事节点类型：开端、情节点、选择、高潮、结局、分支

### 智能资产管理
- AI驱动的纹理合成
- 程序化几何体生成
- 提示词到资产的转换系统
- 智能资产缓存

### AI工作流画布
- 节点图可视化编程，构建AI管线
- 20+内置节点类型，覆盖11个类别
- 类型化引脚连接，类型安全
- 拓扑执行引擎
- 类别：提示词、AI/图像、AI/文本、AI/视频、AI/音频、输入、输出、采样、潜空间、ControlNet、逻辑、游戏

### 智能团队协作系统
- 三层Agent架构，匹配真实工作室层级
  - 第一层：总监（创意总监、技术总监、制作人）
  - 第二层：部门主管（游戏设计师、主程序员、美术总监等）
  - 第三层：专家（19个专家角色）
- 设计评审和审批工作流
- 代码审查和质量验证流程
- 质量门系统，4个标准5个指标

### Web可视化编辑器（SparkLabs Editor）
- React + TypeScript + Vite + Tailwind CSS
- 11个编辑器面板：仪表盘、游戏工作室、模板、故事、资产、语音、分镜、视频、工作流、NPC设计器、Agent面板
- 实时WebSocket连接引擎后端
- AI Agent聊天界面，内容生成
- 可视化工作流画布，拖拽节点
- NPC人格设计器，特质可视化
- 故事编辑器，分支叙事支持

## 系统要求

### 最低要求
- **操作系统**：Windows 10、macOS 10.14、Linux（Ubuntu 18.04+）
- **编译器**：GCC 9+、Clang 10+、MSVC 2019+
- **Python**：3.10+
- **Node.js**：18+
- **内存**：8 GB
- **磁盘**：2 GB 可用空间

### 推荐配置
- **操作系统**：Windows 11、macOS 12+、Linux（Ubuntu 20.04+）
- **编译器**：GCC 11+、Clang 14+、MSVC 2022+
- **内存**：16 GB 或更多
- **GPU**：支持CUDA的NVIDIA GPU（用于GPU加速）

## 安装

### 从源码构建C++引擎

```bash
# 克隆仓库
git clone https://github.com/Yuan-ManX/SparkLabs.git
cd SparkLabs

# 创建构建目录
mkdir build && cd build

# 使用CMake配置
cmake ..

# 构建
cmake --build . --config Release
```

### 设置AI后端

```bash
# 安装Python依赖
pip install -r backend/requirements.txt

# 启动后端服务器
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8090 --reload
```

### 设置Web编辑器

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### CMake选项

- `SPARKLABS_ORT_ENABLED`：启用ONNX Runtime支持（默认：ON）
- `SPARKLABS_GPU_SUPPORT`：启用GPU加速（默认：ON）

```bash
cmake .. -DSPARKLABS_ORT_ENABLED=ON -DSPARKLABS_GPU_SUPPORT=ON
```

## 快速开始

### C++引擎

```cpp
#include <SparkLabs.h>

using namespace SparkLabs;

int main() {
    auto scene = new Scene();
    scene->SetName("MyGame");

    auto player = scene->CreateEntity("Player");
    player->SetPosition(Vector3(0.0f, 1.0f, 0.0f));
    player->SetTag("Player");

    auto npc = scene->CreateEntity("NPC");
    npc->SetPosition(Vector3(5.0f, 1.0f, 0.0f));

    auto npcBrain = npc->AddComponent<NPCBrainComponent>();
    npcBrain->LoadModel("models/npc_decision.onnx");

    Engine::GetInstance()->SetScene(scene);
    Engine::GetInstance()->Run();

    return 0;
}
```

### Python AI Agent

```python
import asyncio
from sparkai import SparkAgent, LLMProvider, LLMConfig, AgentCapability, create_engine_tools

async def main():
    # 创建AI Agent
    agent = SparkAgent(
        name="GameDesigner",
        role="game_designer",
        capabilities=[
            AgentCapability.REASONING,
            AgentCapability.GAMEPLAY_DESIGN,
            AgentCapability.WORLD_BUILDING,
        ],
    )

    # 配置LLM提供商
    llm = LLMProvider(LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="your-api-key",
    ))
    await llm.initialize()
    agent.set_llm_provider(llm)

    # 注册引擎工具
    for tool in create_engine_tools():
        agent.register_tool(tool)

    # 使用Agent
    response = await agent.think("为奇幻RPG设计一个Boss战斗")
    print(response)

    # 执行动作
    result = await agent.act("create_scene", {"name": "Boss竞技场"})
    print(result)

asyncio.run(main())
```

### Python工作流系统

```python
from sparkai import WorkflowGraph, WorkflowNode, WorkflowExecutor, NodeRegistry

# 创建工作流图
graph = WorkflowGraph(name="图像生成管线")

# 使用节点注册表创建类型化节点
registry = NodeRegistry.get_instance()

prompt = registry.create_node("text_prompt", name="风景提示词")
prompt.set_property("prompt", "日落时分的美丽风景")
prompt.position = [100.0, 100.0]

image_gen = registry.create_node("image_generation", name="生成图像")
image_gen.set_property("width", 1024)
image_gen.set_property("height", 1024)
image_gen.position = [400.0, 100.0]

save = registry.create_node("save_image", name="保存结果")
save.set_property("output_path", "output/landscape.png")
save.position = [700.0, 100.0]

# 添加节点并连接
graph.add_node(prompt)
graph.add_node(image_gen)
graph.add_node(save)
graph.connect(prompt.id, 0, image_gen.id, 0)
graph.connect(image_gen.id, 0, save.id, 0)

# 执行
executor = WorkflowExecutor()
result = await executor.execute(graph)
```

### Python NPC系统

```python
from sparkai import NPCBrain, NPCPersonality, PersonalityTraits, BehaviorTree, BehaviorNode

# 创建带人格的NPC
personality = NPCPersonality(
    name="贤者长老",
    traits=PersonalityTraits(
        courage=0.3, curiosity=0.8, aggression=0.1,
        friendliness=0.9, honesty=0.9, intelligence=0.95,
    ),
    background="一位古老的知识守护者",
    speech_style="wise",
)

brain = NPCBrain(personality=personality)

# 添加目标
brain.add_goal("分享智慧", priority=0.8)
brain.add_goal("保护图书馆", priority=0.9)

# 创建行为树
tree = BehaviorTree()
root = BehaviorNode(name="Root", node_type="selector")
tree.set_root(root)
brain.set_behavior_tree(tree)

# 做出决策
decision = await brain.decide({"player_action": "询问古代神器"})
dialogue = await brain.generate_dialogue("告诉我关于古代神器的事")
```

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    SparkLabs Web 编辑器                          │
│  React + TypeScript + Vite + Tailwind CSS                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  游戏    │ │ 工作流   │ │   NPC    │ │     Agent        │   │
│  │  工作室  │ │   画布   │ │  设计器  │ │     面板         │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    后端 API (FastAPI)                            │
│  WebSocket │ REST API │ Agent路由 │ Engine路由                  │
├─────────────────────────────────────────────────────────────────┤
│                    sparkai (Python AI层)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐   │
│  │   Agent     │ │  工作流     │ │      NPC系统            │   │
│  │  基础层     │ │   引擎     │ │  大脑│记忆│情绪         │   │
│  │ LLM│记忆    │ │ 图│执行器  │ │  行为│人格               │   │
│  │ 工具│编排   │ │ 注册表     │ │  对话│目标               │   │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐   │
│  │  叙事引擎   │ │   团队     │ │      引擎               │   │
│  │ 故事│任务   │ │ 总监│主管  │ │  场景│实体               │   │
│  │ 分支│变量   │ │ 专家│质量  │ │  组件系统               │   │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    C++ 核心引擎层                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  场景    │ │  资源    │ │  物理    │ │   AI运行时       │   │
│  │  管理器  │ │  管理器  │ │   引擎  │ │ ONNX│神经        │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    神经渲染管线                                  │
│  经典渲染 → 神经AA → 神经AO → 神经上采样                      │
├─────────────────────────────────────────────────────────────────┤
│                    平台层                                       │
│         Windows | macOS | Linux | Web | 移动端                  │
└─────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
SparkLabs/
├── sparkai/                 # Python AI Agent基础层
│   ├── __init__.py          # 包导出
│   ├── config.py            # 配置系统
│   ├── agent/               # Agent核心
│   │   ├── base.py          # SparkAgent，观察-思考-行动循环
│   │   ├── llm.py           # 多提供商LLM集成
│   │   ├── memory.py        # 分层记忆系统
│   │   ├── toolkit.py       # 工具注册表和执行
│   │   └── orchestrator.py  # 多Agent编排
│   ├── engine/              # Python引擎接口
│   │   ├── engine.py        # SparkEngine、Scene、Entity
│   │   └── scene.py         # 场景管理
│   ├── workflow/            # AI工作流系统
│   │   ├── graph.py         # WorkflowGraph、WorkflowNode、PinType
│   │   ├── executor.py      # 拓扑执行引擎
│   │   └── registry.py      # 节点类型注册表，20+类型
│   ├── npc/                 # 智能NPC系统
│   │   ├── brain.py         # NPCBrain，双网络架构
│   │   ├── personality.py   # 10维人格特质
│   │   └── behavior.py      # 行为树系统
│   ├── narrative/           # AI叙事引擎
│   │   ├── story.py         # 分支故事图
│   │   └── quest.py         # 程序化任务生成
│   ├── team/                # 团队协作
│   │   ├── director.py      # 总监Agent（第一层）
│   │   ├── lead.py          # 主管Agent（第二层）
│   │   ├── specialist.py    # 专家Agent（第三层）
│   │   └── quality.py       # 质量门系统
│   ├── ai/                  # C++ AI运行时（头文件）
│   ├── asset/               # 智能资产管理（C++）
│   ├── audio/               # 音频系统（C++）
│   ├── gameplay/            # 自适应游戏玩法（C++）
│   ├── neural/              # 神经渲染（C++）
│   └── editor/              # 编辑器集成（C++）
├── backend/                 # FastAPI后端
│   ├── app.py               # 应用入口
│   ├── websocket.py         # WebSocket处理器
│   ├── requirements.txt     # Python依赖
│   └── routes/              # API路由
│       ├── engine.py        # 引擎控制端点
│       ├── agent.py         # Agent管理端点
│       ├── scene.py         # 场景/实体端点
│       ├── workflow.py      # 工作流端点
│       ├── narrative.py     # 故事/任务端点
│       └── npc.py           # NPC管理端点
├── frontend/                # SparkLabs Web编辑器
│   ├── App.tsx              # 主应用
│   ├── main.tsx             # 入口点
│   ├── index.html           # HTML模板
│   ├── index.css            # 全局样式
│   ├── components/          # UI组件
│   │   ├── SparkLabsHome.tsx      # 着陆页
│   │   ├── WelcomeDashboard.tsx   # 编辑器仪表盘
│   │   ├── GameEditor.tsx         # 游戏工作室
│   │   ├── GameGenerator.tsx      # 模板生成器
│   │   ├── StoryEditor.tsx        # 故事编辑器
│   │   ├── AssetGenerator.tsx     # 资产生成器
│   │   ├── VoiceSynthesizer.tsx   # 语音合成
│   │   ├── StoryboardEditor.tsx   # 分镜编辑器
│   │   ├── VideoRenderer.tsx      # 视频渲染器
│   │   ├── WorkflowEditor.tsx     # 工作流画布
│   │   ├── NPCDesigner.tsx        # NPC设计器
│   │   └── AgentPanel.tsx         # Agent聊天面板
│   ├── hooks/               # 自定义React钩子
│   ├── utils/               # API客户端和工具
│   └── types/               # TypeScript类型定义
├── core/                    # 核心C++工具
├── engine/                  # C++引擎核心
├── render/                  # 渲染系统
├── platform/                # 平台抽象
├── docs/                    # 文档
├── scripts/                 # 构建脚本
└── tests/                   # 单元测试
```


## 文档

完整文档请参阅 [docs](./docs/) 目录：
- [API参考](./docs/API_REFERENCE.md)
- [架构](./docs/ARCHITECTURE.md)
- [AI系统](./docs/AI_SYSTEM.md)
- [构建说明](./docs/BUILD_INSTRUCTIONS.md)

## 贡献

欢迎贡献！请在提交Pull Request之前阅读贡献指南。

## 许可证

SparkLabs引擎采用MIT许可证。详见 [LICENSE](./LICENSE)。

## ⭐ Star历史

如果你喜欢这个项目，请⭐给仓库加星。你的支持帮助我们成长！

<p align="center">
  <a href="https://star-history.com/#Yuan-ManX/SparkLabs&Date">
    <img src="https://api.star-history.com/svg?repos=Yuan-ManX/SparkLabs&type=Date" />
  </a>
</p>
