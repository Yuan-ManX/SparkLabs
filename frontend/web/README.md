# SparkLabs Editor

SparkLabs AI-Native Game Engine Visual Editor — a web-based game development environment that fuses AI Agent intelligence with real-time 3D scene editing.

## Architecture

SparkLabs Editor is built as a standalone React + TypeScript application with the following core systems:

- **Zustand Global State** — Centralized editor state management across all panels and components
- **THREE.js Viewport** — Real-time 3D scene rendering with shadow mapping, PBR materials, and orbit camera
- **AI Service Layer** — Backend connectivity for AI prompt processing, agent creation, and session management
- **Dual-Mode Editing** — Every operation supports both manual editing and AI-driven generation
- **4-Zone Layout** — Left (Scene/Assets/Nodes), Center (Viewport + Console), Right (Inspector/AI Config), Bottom (Console/Timeline/AI Assistant)

## Standalone Usage

### Prerequisites

- Node.js >= 18
- npm >= 9

### Install Dependencies

```bash
cd frontend/web
npm install
```

### Development Server

```bash
npm run dev
```

The editor runs at `http://localhost:3000/SparkLabs/Editor`.

### Production Build

```bash
npm run build
npm run preview
```

### Without Backend

SparkLabs Editor operates in **standalone mode** when the backend is unavailable. All UI features work with local state. AI prompts display generation phases locally. When the backend is connected, prompts are processed through the full agent pipeline.

## Backend Connection

The editor proxies API requests to `http://localhost:8000` by default. Start the backend:

```bash
cd /path/to/SparkLabs
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

When connected, the status bar shows "Backend Connected" (green). Otherwise, it shows "Standalone Mode" (yellow).

## Editor Features

| Feature | Description |
|---------|-------------|
| AI Prompt Bar | Natural language game creation with Ctrl+K shortcut |
| 3D Viewport | THREE.js scene with Scene/Game/Wireframe modes |
| Scene Outliner | Hierarchical entity tree with visibility/lock toggles |
| Property Editor | Transform, Neural, Rendering, Physics sections |
| Node Graph | Visual programming for game logic |
| Asset Library | Browse and manage game assets |
| Console | Real-time log output with AI integration |
| AI Config | Neural parameter tuning for generation |
| 30+ Mode Panels | Game Studio, Story Editor, NPC Designer, Workflow Editor, etc. |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+1 | Move Tool |
| Ctrl+2 | Rotate Tool |
| Ctrl+3 | Scale Tool |
| Ctrl+P | Toggle Play/Stop |
| Ctrl+E | Script Editor |
| Ctrl+, | Settings |
| Ctrl+D | Dashboard |
| Ctrl+K | Focus AI Prompt |

## Tech Stack

- React 18 + TypeScript
- Vite 5
- THREE.js
- Zustand
- Tailwind CSS
- Lucide React Icons
