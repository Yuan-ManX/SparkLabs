# Spark Labs

**AI-Native Game Engine, Ignite Your Infinite Play! 💥🎮**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![C++](https://img.shields.io/badge/C%2B%2B-17-orange)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

SparkLabs is a next-generation AI-native game engine that deeply integrates artificial intelligence capabilities into the core architecture of game development. Unlike traditional game engines that rely on manually coded game logic and predefined pipelines, SparkLabs revolutionizes game development by enabling procedural content generation, intelligent NPC behavior systems, adaptive rendering, and dynamic difficulty adjustment through AI.

## Key Features

### AI-Native Architecture
- Deep integration of AI inference capabilities into core engine architecture
- AI-driven object system and event handling mechanisms
- Support for neural network models (ONNX Runtime integration)

### Neural Rendering Pipeline
- Real-time AI super-resolution (Neural Upscaling)
- AI-based ambient occlusion (N/AO)
- Intelligent anti-aliasing (Neural AA)
- Adaptive rendering based on scene understanding

### Intelligent NPC System
- Neural network-driven NPC decision making
- Memory system with short-term, long-term, episodic, and semantic memory
- Attention mechanism for focus management
- Emotional state machine with PAD model
- Context-aware dialogue generation

### Adaptive Gameplay
- Player skill tracking and modeling
- Real-time dynamic difficulty adjustment
- Engagement metrics monitoring
- Personalized player experience optimization

### AI Narrative Engine
- Procedural story generation with branching narratives
- Dynamic quest generation
- Context-aware dialogue and narrative elements
- Adaptive reward system based on player preferences

### Smart Asset Management
- AI-powered texture synthesis
- Procedural geometry generation
- Prompt-to-asset conversion system
- Intelligent asset caching

## System Requirements

### Minimum Requirements
- **OS**: Windows 10, macOS 10.14, Linux (Ubuntu 18.04+)
- **Compiler**: GCC 9+, Clang 10+, MSVC 2019+
- **RAM**: 8 GB
- **Disk**: 2 GB free space

### Recommended Requirements
- **OS**: Windows 11, macOS 12+, Linux (Ubuntu 20.04+)
- **Compiler**: GCC 11+, Clang 14+, MSVC 2022+
- **RAM**: 16 GB or more
- **GPU**: NVIDIA GPU with CUDA support (for GPU acceleration)

## Installation

### Building from Source

```bash
# Clone the repository
git clone https://github.com/Yuan-ManX/SparkLabs.git
cd SparkLabs

# Create build directory
mkdir build && cd build

# Configure with CMake
cmake ..

# Build
cmake --build . --config Release

# Run
./SparkLabs
```

### CMake Options

- `SPARKLABS_ORT_ENABLED`: Enable ONNX Runtime support (default: ON)
- `SPARKLABS_GPU_SUPPORT`: Enable GPU acceleration (default: ON)

```bash
cmake .. -DSPARKLABS_ORT_ENABLED=ON -DSPARKLABS_GPU_SUPPORT=ON
```

## Quick Start

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

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SparkLabs Engine                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   sparkai   │  │   Neural    │  │      Adaptive       │  │
│  │    Core     │  │   Renderer  │  │      Gameplay       │  │
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

## Module Descriptions

### Core (`core/`)
Essential utilities and types used throughout the engine:
- **Math**: Vector2, Vector3, Vector4, Matrix4x4, Quaternion
- **Memory**: SmartPtr, WeakPtr with reference counting
- **Object**: Base Object class with RTTI system
- **String**: UTF-8 string with hashing support

### Engine (`engine/`)
Core game engine functionality:
- **Scene**: Scene graph, GameObject, Component system
- **Resource**: Async resource loading, caching, hot reload

### sparkai (`sparkai/`)
AI-native modules - the core AI components of SparkLabs:
- **AI Core**: AIBrain, Blackboard, EventBus, NeuralNetwork
- **Behavior**: Behavior Tree with Composite, Decorator, Action nodes
- **ONNX**: ONNX Runtime integration for neural network inference
- **NPC**: Neural NPC brain, memory, attention, emotional state
- **Gameplay**: Player model, difficulty controller, engagement metrics
- **Narrative**: Story graph, quest generator, dialogue system
- **Asset**: AI-powered asset generation, texture synthesis
- **Render/Neural**: Neural upscaling, ambient occlusion, anti-aliasing
- **Editor**: AI-integrated editor panels

### Render (`render/`)
Rendering system:
- **GPU**: GPU resource management
- **Shader**: Shader and ShaderProgram management
- **Mesh**: 3D mesh loading and management
- **Material**: Material system
- **Texture**: Texture loading and management
- **Neural**: AI-enhanced rendering effects

### Platform (`platform/`)
Platform abstraction:
- **FileSystem**: Cross-platform file operations
- **Input**: Keyboard, mouse, gamepad input
- **Timer**: High-precision timing
- **Window**: Window management

## Documentation

For full documentation, see the [docs](./docs/) directory:
- [API Reference](./docs/API_REFERENCE.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [AI System](./docs/AI_SYSTEM.md)
- [Building Instructions](./docs/BUILD_INSTRUCTIONS.md)

## Project Structure

```
SparkLabs/
├── core/                 # Core utilities (math, memory, object, string)
├── engine/              # Engine core (scene, resource)
├── sparkai/             # AI-native modules
│   ├── ai/              # AI runtime (behavior, brain, onnx)
│   ├── npc/            # Intelligent NPC system
│   ├── gameplay/       # Adaptive gameplay
│   ├── narrative/      # AI narrative engine
│   ├── asset/          # Smart asset management
│   ├── render/neural/  # Neural rendering
│   └── editor/         # AI editor tools
├── render/              # Rendering system
├── platform/            # Platform abstraction
├── docs/                # Documentation
├── scripts/             # Build scripts
├── tests/               # Unit tests
└── main.cpp            # Entry point
```

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License

SparkLabs Engine is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

## Acknowledgments

Special thanks to all contributors and the open-source community for making game development accessible to everyone.

---

**SparkLabs Engine** - Empowering game developers with AI-native technology.
