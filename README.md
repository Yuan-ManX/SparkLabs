<div align="center">

<img src="./assets/SparkLabs-Logo.png" alt="SparkLabs Logo">

**The First AI-Native Game Engine.** 💥

**Ignite Your Infinite Play!** 🎮

Where AI Agents design worlds, direct narratives, and breathe life into every pixel — not as plugins layered on top, but as the very foundation the engine is built from. A new paradigm where creation, cognition, and play converge.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Stars](https://img.shields.io/github/stars/Yuan-ManX/SparkLabs?style=social)
![Modules](https://img.shields.io/badge/modules-900+-purple)

![SparkLabs-Video](./assets/SparkLabs-Video.gif)

[Website](https://yuan-manx.github.io/SparkLabs/) · [SparkLabs](#what-is-sparklabs) · [Innovation](#innovation) · [Quickstart](#quick-start) · [Features](#features) · [Contributing](#contributing)

#### [English](./README.md) | [中文文档](./README_CN.md)

</div>


## What is SparkLabs?

SparkLabs is an **AI-native game engine** where intelligence is not a feature bolted on top — it is the substrate everything is built from. Every subsystem, from physics to NPC cognition to narrative pacing, is designed around intelligent agents that perceive, reason, and act. This is AI-native game development: not using AI to help make a game, but making a game *with* AI at the core of every system.

The world has seen game engines with AI assistants. AI that generates assets. AI that writes dialogue. But no one has built an engine where the AI *is* the engine — where game logic emerges from agent deliberation rather than hand-coded state machines, where NPCs possess genuine cognitive architecture with memory and beliefs, where the engine itself thinks alongside you as you build. SparkLabs explores a new paradigm of interactive content creation, one where the boundary between creator, tool, and creation dissolves.

SparkLabs is that engine. It is the AI-native counterpart to the traditional game engines that define the industry — not a rendering pipeline with an AI chatbot grafted on, but a platform architected from first principles around one conviction: **AI is not a tool you call. It is the foundation you build on.**


## Why "SparkLabs"?

The name SparkLabs carries a deliberate duality.

A spark is the moment of creation — the flash of an idea, the ignition of imagination, the instant something new comes into being. In game development, every world begins with a spark: a what-if, a vision, a dream of something that does not yet exist. SparkLabs is built to catch that spark and fan it into a living, playable reality — a new paradigm where human creativity and AI cognition ignite each other.

At a deeper level, SparkLabs is a laboratory — a space where AI agents and human creators experiment together, iterate rapidly, and discover gameplay possibilities that neither could reach alone. The "labs" is intentional: it is not a factory producing predetermined output, but a workshop where emergence is welcomed, where new forms of interactive content are discovered rather than assembled, and where the unexpected is celebrated.

Most engines treat AI as a productivity tool. SparkLabs treats it as a **creative collaborator** — agents that do not wait to be prompted, but participate in the act of creation itself, expanding what a game can be and how it comes to be.


## Innovation

### The Engine Thinks

In SparkLabs, the engine is not a passive runtime waiting for instructions. It is an active participant in the development process — a new form of interactive content creation where the tool understands what you are building. When you place an entity in a scene, agents analyze the context and suggest behaviors. When you design a combat encounter, agents simulate balance outcomes before you hit play. When you write a quest, agents trace the narrative graph for contradictions and dead ends.

This is not an AI assistant watching you work. It is a creative partner thinking alongside you — one that understands the full state of your game and contributes to its evolution. The engine does not just execute your vision; it participates in shaping it.

### Agents Are the Architecture

Traditional engines expose APIs that humans call. SparkLabs exposes APIs that *agents* call — and agents are first-class citizens of the engine itself. This is the AI Agent-native architecture: 457 agent modules span game design, world building, NPC cognition, narrative direction, combat balancing, live-ops, testing, and production. They do not live outside the engine. They are the engine.

An NPC in SparkLabs does not follow a scripted state machine. It possesses a cognitive architecture — beliefs, desires, intentions, memory, emotion, personality traits, attention mechanisms, and the capacity to dream. It forms relationships that deepen over time. It makes decisions that emerge from its internal model of the world, not from a switch statement. This is a new form of interactive character — not an actor reading lines, but a being inhabiting a world.

### A Spectrum of Cognition

SparkLabs does not believe in one-size-fits-all intelligence. Different game-development challenges require different reasoning paradigms — and the engine's Unified Cognitive Core can switch between them fluidly: BDI for goal-directed behavior, HTN for hierarchical planning, behavior trees for reactive control, causal graphs for understanding consequence, counterfactual simulation for evaluating alternatives, and chain-of-thought for deliberate reasoning.

An agent designing a boss encounter uses HTN to decompose the problem. An NPC deciding whether to flee uses BDI to weigh its beliefs against its desires. A narrative agent checking story consistency uses causal reasoning to trace ripple effects across the plot graph. The paradigm serves the task — not the other way around. This cognitive diversity is what allows AI-native game development to handle the full complexity of game creation.

### Worlds That Emerge

Most game worlds are assembled by hand — every encounter placed, every line of dialogue written, every balance number tuned through playtesting. SparkLabs shifts this from assembly to cultivation: a new paradigm where worlds grow rather than get built. Agents design worlds, compose assets, direct narratives, balance economies, and adapt the live experience to each player — not through rigid procedural generation, but through genuine creative deliberation.

The result is not random content. It is content that emerges from coherent creative intent, shaped by agents that understand the design goals and the player's journey. Every playthrough can be different; every player's world can be their own.

### The Engine Tests Itself

When you change a system in SparkLabs, agents do not wait for a human QA pass. They simulate. They spawn playthroughs, probe edge cases, hunt for exploits, and trace crash signatures back to their root cause. The engine's 457 agent modules include a full testing spectrum — autonomous testers, bug hunters, performance profilers, and bug forensics agents that reproduce issues from telemetry alone.

This is not test automation. It is test *intelligence* — agents that understand what the game is supposed to do and verify that it still does, closing the loop between creation and validation in a single AI-native workflow.


## Quick Start

> SparkLabs is under active development. The full runtime requires LLM API configuration.

```bash
git clone https://github.com/Yuan-ManX/SparkLabs.git
cd SparkLabs

# Start the backend
pip install -r backend/requirements.txt
python -m uvicorn backend.app:app

# Start the frontend editor
cd frontend/web
npm install
npm run dev
```


## Features

| Dimension | Capabilities |
|---|---|
| **AI-Native Agent Architecture** | 457 agent modules across game design, world building, NPC cognition, narrative, combat, testing, and production. Unified Cognitive Core switches between BDI, HTN, behavior trees, causal reasoning, and chain-of-thought. |
| **Intelligent NPCs** | Cognitive architecture with 10-dimensional personality, 7-emotion state machine, four-layer memory, attention mechanism, dream simulation, and LLM-driven context-aware dialogue. NPCs are agents, not actors. |
| **AI Narrative Engine** | Branching story graphs, procedural quest generation, emergent storytelling from NPC interactions, causal graph engine, counterfactual simulation for "what-if" reasoning. |
| **Full-Spectrum Physics** | AABB tree broadphase, SAT/GJK narrowphase, continuous collision detection, soft body deformation, fluid dynamics, electromagnetic fields, chemical reactions, thermal dynamics, orbital mechanics. |
| **Neural Rendering** | AI super-resolution, neural ambient occlusion, neural anti-aliasing, shader material graph system, visual filters, optics simulation, adaptive rendering. |
| **Multi-Agent Orchestration** | Teams with role assignment, task delegation, dependency-aware scheduling, voting and consensus, conflict resolution, resource allocation, and coalition negotiation. |
| **AI Workflow Canvas** | Node-graph visual programming with 20+ typed node types across 11 categories, topological execution engine, and real-time preview at every node. |
| **Autonomous Testing** | Agents that simulate playthroughs, probe edge cases, hunt exploits, trace crash signatures, and reproduce bugs from telemetry — the engine tests itself. |
| **AI Live-Ops** | Predictive content direction, player sentiment analysis, adaptive difficulty, A/B testing, anti-cheat direction, and real-time balance optimization. |
| **Web Visual Editor** | 40+ editor panels, real-time WebSocket, AI agent chat, visual workflow canvas, NPC personality designer, story editor — high-contrast black-and-white design. |


## Use Cases

#### For Solo Developers

One person with a vision and a team of agents. You describe the game you want to make; agents help design the systems, generate the assets, write the dialogue, balance the combat, and test the build. The engine does not replace your creativity — it amplifies it, handling the parts that used to require a studio so you can focus on the spark. This is AI-native game development at its most democratic: a solo creator wielding the creative power of an entire team.

#### For Studios

A studio where every developer is paired with a team of agents. Your designers iterate on gameplay with agents that simulate balance outcomes in real time. Your artists collaborate with agents that harmonize asset styles and optimize performance. Your QA team works alongside agents that never sleep, running simulations across every corner of the game. Not "AI-assisted development" — just **development**, with more capable teammates. The AI Agent-native architecture means your studio's workflow adapts to human intent, not the other way around.

#### For Live Games

A game that adapts. Agents monitor player sentiment, predict churn, detect balance issues before they become meta problems, generate seasonal content tuned to the community, and direct live events that respond to the room. The game does not wait for a patch cycle to improve. It evolves continuously, guided by agents that understand the player base as deeply as the design. This is a new paradigm of live interactive content — not games that are maintained, but games that are alive.

#### for Researchers

A laboratory for AI-native game intelligence. SparkLabs provides a full-spectrum testbed for multi-agent collaboration, cognitive NPC architecture, emergent narrative, procedural content generation, and autonomous game testing — with 6800+ API routes and 883,000+ lines of agent code ready to be extended, modified, and studied. A playground for exploring new forms of AI-driven interactive content and the future of game creation itself.


## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.


## License

SparkLabs is licensed under the MIT License. See [LICENSE](./LICENSE) for details.


## ⭐ Star History

If you like this project, please ⭐ star the repo. Your support helps us grow!

<p align="center">
  <a href="https://star-history.com/#Yuan-ManX/SparkLabs&Date">
    <img src="https://api.star-history.com/svg?repos=Yuan-ManX/SparkLabs&type=Date" />
  </a>
</p>
