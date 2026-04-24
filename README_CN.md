<div align="center">

<img src="./assets/SparkLabs-Logo.png" alt="SparkLabs Logo"/>

# Spark Labs

### AI 原生游戏引擎 💥
### 点燃你的无限游戏 🎮

![版本](https://img.shields.io/badge/version-1.0.0-blue)
![C++](https://img.shields.io/badge/C%2B%2B-17-orange)
![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg)
![许可证](https://img.shields.io/badge/license-MIT-green)
![Stars](https://img.shields.io/github/stars/Yuan-ManX/SparkLabs?style=social)


### [English](./README.md) | [中文文档](./README_CN.md)

</div>


## 概述

**SparkLabs** 是一款新一代的AI原生游戏引擎，将人工智能能力深度融入游戏开发的核心架构中。传统游戏引擎依赖手工编码的游戏逻辑和预定义的资源管道，而 SparkLabs 通过AI驱动的程序化内容生成、智能NPC行为系统、自适应渲染和动态难度调整，彻底革新游戏开发范式。

## 核心特性

### AI原生架构
- AI推理能力深度集成到核心引擎架构
- AI驱动的对象系统和事件处理机制
- 神经网络模型支持（ONNX Runtime集成）

### 神经渲染管线
- 实时AI超分辨率（神经上采样）
- AI环境光遮蔽（N/AO）
- 智能抗锯齿（神经AA）
- 基于场景理解的自适应渲染

### 智能NPC系统
- 神经网络驱动的NPC决策系统
- 记忆系统（短时记忆、长时记忆、情景记忆、语义记忆）
- 注意力机制用于焦点管理
- 基于PAD模型的情感状态机
- 上下文感知的对话生成

### 自适应游戏玩法
- 玩家技能追踪与建模
- 实时动态难度调整
- 参与度指标监控
- 个性化玩家体验优化

### AI叙事引擎
- 分支叙事的程序化故事生成
- 动态任务生成
- 上下文感知的对话和叙事元素
- 基于玩家偏好的自适应奖励系统

### 智能资源管理
- AI驱动的纹理合成
- 程序化几何体生成
- 提示词转资产系统
- 智能资源缓存

### 智能团队协作系统
- 三层架构的代理体系，匹配真实工作室层级
  - 第一层：总监（创意总监、技术总监、制作人）
  - 第二层：部门主管（游戏设计师、主程序员、美术总监等）
  - 第三层：专家（游戏玩法程序员、关卡设计师、音效设计师等）
- 全面的任务管理和分配系统
- 实时进度跟踪和报告
- 设计评审和批准工作流
- 代码评审和质量验证流程

### 高级工作流管理
- 25+个预定义工作流模板，用于常见开发任务
  - 头脑风暴会议、冲刺规划、设计评审、代码评审
  - 平衡性检查、资源审计、范围检查、性能分析
  - 里程碑评审、估算、回顾、bug报告
  - 发布清单、启动清单、变更日志、补丁说明
  - 团队协作工作流（战斗、叙事、UI、音频、关卡设计）
- 自定义工作流创建和注册
- 逐步工作流执行和跟踪
- 工作流历史和审计追踪

### 质量保证与验证
- 多级质量标准（低、中、高、生产级）
- 全面的质量指标跟踪
  - 代码质量评估
  - 性能基准测试
  - 文档覆盖度验证
  - 测试覆盖度监控
  - 无障碍合规性检查
- 自动化质量关卡验证
- 质量报告生成

## 系统要求

### 最低要求
- **操作系统**: Windows 10, macOS 10.14, Linux (Ubuntu 18.04+)
- **编译器**: GCC 9+, Clang 10+, MSVC 2019+
- **内存**: 8 GB
- **硬盘**: 2 GB 可用空间

### 推荐要求
- **操作系统**: Windows 11, macOS 12+, Linux (Ubuntu 20.04+)
- **编译器**: GCC 11+, Clang 14+, MSVC 2022+
- **内存**: 16 GB 或更多
- **显卡**: NVIDIA 显卡，支持CUDA（用于GPU加速）

## 安装

### 从源码构建

```bash
# 克隆仓库
git clone https://github.com/Yuan-ManX/SparkLabs.git
cd SparkLabs

# 创建构建目录
mkdir build && cd build

# CMake配置
cmake ..

# 编译
cmake --build . --config Release

# 运行
./SparkLabs
```

### CMake选项

- `SPARKLABS_ORT_ENABLED`: 启用ONNX Runtime支持（默认: ON）
- `SPARKLABS_GPU_SUPPORT`: 启用GPU加速（默认: ON）

```bash
cmake .. -DSPARKLABS_ORT_ENABLED=ON -DSPARKLABS_GPU_SUPPORT=ON
```

## 快速开始

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

### Python API

SparkLabs提供Python绑定层，方便快速原型开发和脚本编写：

```python
import sparklabs

# 创建工作流图
graph = sparklabs.WorkflowGraph()
graph.set_name("我的AI工作流")

# 创建并配置节点
prompt = sparklabs.create_text_prompt_node()
prompt.set_id("prompt_1")
prompt.set_prompt("美丽的日落山景")
prompt.set_position(100.0, 100.0)

image_gen = sparklabs.create_image_generation_node()
image_gen.set_id("image_gen_1")
image_gen.set_model("models/sd_xl.safetensors")
image_gen.set_width(1024)
image_gen.set_height(1024)
image_gen.set_steps(30)
image_gen.set_position(400.0, 100.0)

save_image = sparklabs.create_save_image_node()
save_image.set_id("save_1")
save_image.set_output_path("output/landscape.png")
save_image.set_position(700.0, 100.0)

# 连接节点并执行
graph.add_node(prompt)
graph.add_node(image_gen)
graph.add_node(save_image)
graph.connect("prompt_1", 0, "image_gen_1", 0)
graph.connect("image_gen_1", 0, "save_1", 0)
result = graph.execute()
```

### 使用AI工作流画布

```cpp
auto canvas = new WorkflowCanvas();
auto graph = new WorkflowGraph();

canvas->SetGraph(graph);

auto textPrompt = new TextPromptNode();
textPrompt->SetPrompt("A beautiful landscape at sunset");
canvas->AddNode(textPrompt, 100.0f, 100.0f);

auto imageGen = new ImageGenerationNode();
imageGen->SetModel("models/sd_xl.safetensors");
imageGen->SetSteps(30);
imageGen->SetWidth(1024);
imageGen->SetHeight(1024);
canvas->AddNode(imageGen, 400.0f, 100.0f);

auto saveImage = new SaveImageNode();
canvas->AddNode(saveImage, 700.0f, 100.0f);

canvas->Connect(textPrompt->GetId(), 0, imageGen->GetId(), 0);
canvas->Connect(imageGen->GetId(), 0, saveImage->GetId(), 0);

canvas->Execute();
```

## AI工作流画布界面

### 节点类别

| 类别 | 节点 | 描述 |
|------|------|------|
| **AI/Image** | Image Generation, Inpaint, Upscale | 图像创建和修改 |
| **AI/Text** | Text Generation, Prompt Templates | 文本和对话创建 |
| **AI/Video** | Video Generation, Video Edit | 视频内容创建 |
| **AI/Audio** | Audio Generation, TTS | 声音和音乐创建 |
| **Input** | Load Image, Load Audio, Load Video | 资源加载 |
| **Output** | Save Image, Save Video, Save Audio | 资源保存 |
| **Model** | Load Model, Load Checkpoint, Load VAE | 模型管理 |
| **Prompt** | Text Prompt, Negative Prompt, Wildcards | 提示词工程 |
| **Sampling** | KSampler, KSampler Advanced | 扩散采样 |
| **Latent** | Empty Latent, VAE Encode, VAE Decode | 潜空间操作 |
| **ControlNet** | ControlNet Apply, ControlNet Loader | ControlNet集成 |

### 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Enter | 将工作流加入生成队列 |
| Ctrl+Shift+Enter | 优先队列生成 |
| Ctrl+Z | 撤销 |
| Ctrl+Y | 重做 |
| Ctrl+C | 复制节点 |
| Ctrl+V | 粘贴节点 |
| Ctrl+A | 全选节点 |
| Delete | 删除所选 |
| Space+拖动 | 平移画布 |
| Alt+滚轮 | 缩放 |

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     SparkLabs Engine                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   AI工作流画布                            ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     ││
│  │  │   文本   │→│    图像   │→│   VAE    │→│   保存   │     ││
│  │  │   提示   │  │  生成   │  │   解码   │  │   图像   │     ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘     ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   sparkai   │  │   Neural    │  │      Adaptive       │  │
│  │   Core      │  │   Renderer  │  │      Gameplay       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    Smart    │  │   Neural    │  │   AI Narrative      │  │
│  │    Asset    │  │   NPC Brain │  │      Engine         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Core Engine Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │  Scene   │ │ Resource │ │ Physics  │ │  Scripting   │    │
│  │ Manager  │ │ Manager  │ │  Engine  │ │    System    │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Platform Layer                           │
│         Windows | macOS | Linux | Web | Mobile              │
└─────────────────────────────────────────────────────────────┘
```

## 模块说明

### Core (`core/`)
引擎核心工具和类型：
- **Math**: Vector2, Vector3, Vector4, Matrix4x4, Quaternion
- **Memory**: SmartPtr, WeakPtr 引用计数智能指针
- **Object**: 基类对象，RTTI系统
- **String**: UTF-8字符串，带哈希支持

### Engine (`engine/`)
核心游戏引擎功能：
- **Scene**: 场景图、GameObject、组件系统
- **Resource**: 异步资源加载、缓存、热重载

### sparkai (`sparkai/`)
AI原生模块 - SparkLabs的核心AI组件：
- **Workflow**: AI工作流画布系统
  - `workflow/WorkflowGraph.h`: 图、节点、引脚、边定义
  - `workflow/WorkflowFactory.h`: 节点注册、序列化、执行器
  - `workflow/nodes/AIGenerationNodes.h`: 图像、文本、视频、音频生成节点
  - `ui/WorkflowCanvas.h`: 画布、调色板、属性面板、队列
- **AI Core**: AIBrain、Blackboard、EventBus、NeuralNetwork
- **Behavior**: 行为树（组合节点、装饰器节点、动作节点）
- **ONNX**: ONNX Runtime集成
- **NPC**: 神经NPC大脑、记忆、注意力、情感状态
- **Gameplay**: 玩家模型、难度控制器、参与度指标
- **Narrative**: 故事图、任务生成器、对话系统
- **Asset**: AI资源生成、纹理合成
- **Render/Neural**: 神经上采样、环境光遮蔽、抗锯齿
- **Editor**: AI集成编辑器面板

### Render (`render/`)
渲染系统：
- **GPU**: GPU资源管理
- **Shader**: Shader和ShaderProgram管理
- **Mesh**: 3D网格加载和管理
- **Material**: 材质系统
- **Texture**: 纹理加载和管理
- **Neural**: AI增强渲染效果

### Platform (`platform/`)
平台抽象：
- **FileSystem**: 跨平台文件操作
- **Input**: 键盘、鼠标、手柄输入
- **Timer**: 高精度计时
- **Window**: 窗口管理

## 文档

更多文档请参阅 [docs](./docs/) 目录：
- [API参考](./docs/API_REFERENCE.md)
- [架构](./docs/ARCHITECTURE.md)
- [AI系统](./docs/AI_SYSTEM.md)
- [构建指南](./docs/BUILD_INSTRUCTIONS.md)

## 项目结构

```
SparkLabs/
├── core/                 # 核心工具（数学、内存、对象、字符串）
├── engine/              # 引擎核心（场景、资源）
├── sparkai/             # AI原生模块
│   ├── ai/              # AI运行时（行为、大脑、onnx）
│   ├── team/            # 团队协作系统
│   │   ├── TeamAgent.h/cpp
│   │   ├── TeamDirector.h/cpp
│   │   ├── TeamLead.h/cpp
│   │   ├── TeamSpecialist.h/cpp
│   │   ├── TeamOrchestrator.h/cpp
│   │   ├── QualityGate.h/cpp
│   │   └── WorkflowManager.h/cpp
│   ├── workflow/        # AI工作流画布系统
│   │   ├── WorkflowGraph.h
│   │   ├── WorkflowFactory.h
│   │   └── nodes/
│   │       └── AIGenerationNodes.h
│   ├── ui/              # AI工作流UI组件
│   ├── npc/            # 智能NPC系统
│   ├── gameplay/       # 自适应游戏玩法
│   ├── narrative/      # AI叙事引擎
│   ├── asset/          # 智能资源管理
│   ├── render/neural/  # 神经渲染
│   └── editor/         # AI编辑器工具
├── render/              # 渲染系统
├── platform/            # 平台抽象
├── docs/                # 文档
├── scripts/             # 构建脚本
├── tests/               # 单元测试
└── main.cpp            # 入口点
```

## 贡献

欢迎贡献！请在提交拉取请求之前阅读我们的贡献指南。

## 许可证

SparkLabs Engine 基于MIT许可证授权。详见 [LICENSE](./LICENSE)。

## 致谢

特别感谢所有贡献者和开源社区，让游戏开发对每个人都可以触及。


## ⭐ 星标历史

如果您喜欢这个项目，请 ⭐ 给仓库加星。您的支持帮助我们成长！

<p align="center">
  <a href="https://star-history.com/#Yuan-ManX/SparkLabs&Date">
    <img src="https://api.star-history.com/svg?repos=Yuan-ManX/SparkLabs&type=Date" />
  </a>
</p>


**SparkLabs** - 用AI原生技术赋能游戏开发者。
