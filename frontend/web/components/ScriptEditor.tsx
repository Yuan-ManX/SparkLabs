import React, { useState, useCallback, useRef, useEffect } from 'react';

interface ScriptFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
}

const KEYWORDS_JS = ['function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'return', 'class', 'import', 'export', 'default', 'new', 'this', 'async', 'await', 'try', 'catch', 'throw', 'switch', 'case', 'break', 'continue', 'typeof', 'instanceof', 'extends', 'super', 'static', 'get', 'set'];
const KEYWORDS_PY = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'return', 'import', 'from', 'as', 'try', 'except', 'raise', 'with', 'yield', 'lambda', 'pass', 'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None', 'self', 'async', 'await'];
const BUILTINS_JS = ['console', 'Math', 'Array', 'Object', 'String', 'Number', 'Promise', 'setTimeout', 'setInterval', 'document', 'window', 'fetch', 'JSON'];
const BUILTINS_PY = ['print', 'len', 'range', 'list', 'dict', 'set', 'tuple', 'str', 'int', 'float', 'bool', 'type', 'isinstance', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'open', 'super'];

const SEED_FILES: ScriptFile[] = [
  {
    id: 'f1', name: 'PlayerController.js', language: 'javascript',
    content: `class PlayerController {\n  constructor(entity) {\n    this.entity = entity;\n    this.speed = 5.0;\n    this.jumpForce = 12.0;\n    this.isGrounded = false;\n    this.health = 100;\n  }\n\n  update(deltaTime) {\n    const input = this.entity.getInput();\n    \n    if (input.moveLeft) {\n      this.entity.velocity.x = -this.speed;\n    } else if (input.moveRight) {\n      this.entity.velocity.x = this.speed;\n    } else {\n      this.entity.velocity.x *= 0.85;\n    }\n    \n    if (input.jump && this.isGrounded) {\n      this.entity.velocity.y = this.jumpForce;\n      this.isGrounded = false;\n    }\n    \n    this.entity.applyGravity(deltaTime);\n    this.entity.updatePosition(deltaTime);\n  }\n\n  takeDamage(amount) {\n    this.health -= amount;\n    if (this.health <= 0) {\n      this.onDeath();\n    }\n  }\n\n  onDeath() {\n    console.log('Player defeated');\n    this.entity.triggerEvent('playerDeath');\n  }\n}`,
    modified: false,
  },
  {
    id: 'f2', name: 'EnemyAI.py', language: 'python',
    content: `class EnemyAI:\n    def __init__(self, entity):\n        self.entity = entity\n        self.patrol_points = []\n        self.current_point = 0\n        self.detection_range = 8.0\n        self.attack_range = 1.5\n        self.state = "patrol"\n        self.speed = 3.0\n\n    def update(self, delta_time, player_position):\n        distance = self.distance_to(player_position)\n\n        if self.state == "patrol":\n            self._patrol(delta_time)\n            if distance < self.detection_range:\n                self.state = "chase"\n\n        elif self.state == "chase":\n            self._chase(player_position, delta_time)\n            if distance < self.attack_range:\n                self.state = "attack"\n            elif distance > self.detection_range * 1.5:\n                self.state = "patrol"\n\n        elif self.state == "attack":\n            self._attack()\n            if distance > self.attack_range * 1.2:\n                self.state = "chase"\n\n    def _patrol(self, delta_time):\n        if not self.patrol_points:\n            return\n        target = self.patrol_points[self.current_point]\n        self.entity.move_toward(target, self.speed * delta_time)\n        if self.entity.near(target, 0.5):\n            self.current_point = (self.current_point + 1) % len(self.patrol_points)\n\n    def _chase(self, target, delta_time):\n        self.entity.move_toward(target, self.speed * 1.3 * delta_time)\n\n    def _attack(self):\n        self.entity.play_animation("attack")\n        self.entity.deal_damage(10)\n\n    def distance_to(self, position):\n        return self.entity.position.distance_to(position)`,
    modified: false,
  },
  {
    id: 'f3', name: 'GameManager.js', language: 'javascript',
    content: `class GameManager {\n  static instance = null;\n\n  constructor() {\n    if (GameManager.instance) return GameManager.instance;\n    GameManager.instance = this;\n    \n    this.score = 0;\n    this.level = 1;\n    this.gameState = 'menu';\n    this.entities = new Map();\n  }\n\n  startGame() {\n    this.gameState = 'playing';\n    this.score = 0;\n    this.level = 1;\n    this.loadLevel(this.level);\n  }\n\n  loadLevel(levelNum) {\n    this.entities.clear();\n    const levelData = this.generateLevel(levelNum);\n    levelData.entities.forEach(data => {\n      this.spawnEntity(data);\n    });\n  }\n\n  addScore(points) {\n    this.score += points;\n    this.onScoreChanged(this.score);\n  }\n\n  nextLevel() {\n    this.level++;\n    this.loadLevel(this.level);\n  }\n\n  generateLevel(levelNum) {\n    return {\n      entities: [],\n      difficulty: Math.min(levelNum * 0.15, 2.0)\n    };\n  }\n\n  spawnEntity(data) {\n    const id = \`entity_\${Date.now()}\`;\n    this.entities.set(id, data);\n    return id;\n  }\n\n  onScoreChanged(score) {\n    console.log(\`Score: \${score}\`);\n  }\n}`,
    modified: false,
  },
];

const ScriptEditor: React.FC = () => {
  const [files, setFiles] = useState<ScriptFile[]>(SEED_FILES);
  const [activeFileId, setActiveFileId] = useState<string>('f1');
  const [cursorLine, setCursorLine] = useState(1);
  const [cursorCol, setCursorCol] = useState(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeFile = files.find((f) => f.id === activeFileId);

  const handleContentChange = useCallback((content: string) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === activeFileId ? { ...f, content, modified: true } : f))
    );
  }, [activeFileId]);

  const handleCursorChange = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const pos = textarea.selectionStart;
    const text = textarea.value.substring(0, pos);
    const lines = text.split('\n');
    setCursorLine(lines.length);
    setCursorCol(lines[lines.length - 1].length + 1);
  }, []);

  const handleNewFile = useCallback(() => {
    const newFile: ScriptFile = {
      id: `f_${Date.now()}`,
      name: 'NewScript.js',
      language: 'javascript',
      content: '// New game script\n',
      modified: true,
    };
    setFiles((prev) => [...prev, newFile]);
    setActiveFileId(newFile.id);
  }, []);

  const handleSave = useCallback(() => {
    setFiles((prev) =>
      prev.map((f) => (f.id === activeFileId ? { ...f, modified: false } : f))
    );
  }, [activeFileId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  const lineCount = activeFile ? activeFile.content.split('\n').length : 1;

  return (
    <div className="sl-panel h-full">
      <div className="sl-tab-bar">
        {files.map((file) => (
          <button
            key={file.id}
            onClick={() => setActiveFileId(file.id)}
            className={`sl-tab ${activeFileId === file.id ? 'active' : ''}`}
          >
            <i className={`fa-solid ${file.language === 'python' ? 'fa-python' : 'fa-js'} text-[9px] ${file.language === 'python' ? 'text-blue-400' : 'text-yellow-400'}`} />
            {file.name}
            {file.modified && <span className="w-1.5 h-1.5 bg-orange-500 rounded-full ml-1" />}
          </button>
        ))}
        <button onClick={handleNewFile} className="sl-tab text-orange-500">
          <i className="fa-solid fa-plus text-[9px]" />
        </button>
      </div>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-12 bg-[#0a0a0a] border-r border-[#1e1e1e] py-2 text-right pr-2 overflow-hidden select-none flex-shrink-0">
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i} className={`text-[11px] font-mono leading-[20px] ${cursorLine === i + 1 ? 'text-[#555]' : 'text-[#333]'}`}>
              {i + 1}
            </div>
          ))}
        </div>
        <div className="flex-1 relative overflow-hidden">
          <textarea
            ref={textareaRef}
            value={activeFile?.content || ''}
            onChange={(e) => handleContentChange(e.target.value)}
            onKeyUp={handleCursorChange}
            onClick={handleCursorChange}
            className="w-full h-full bg-[#0d0d0d] text-[#ddd] font-mono text-[12px] leading-[20px] p-2 outline-none resize-none border-none"
            spellCheck={false}
          />
        </div>
      </div>
      <div className="h-6 bg-[#0d0d0d] border-t border-[#1e1e1e] flex items-center px-3 text-[10px] text-[#444] font-mono gap-4 flex-shrink-0">
        <span>Ln {cursorLine}, Col {cursorCol}</span>
        <span>UTF-8</span>
        <span>{activeFile?.language === 'python' ? 'Python' : 'JavaScript'}</span>
        <div className="flex-1" />
        <span>{activeFile?.modified ? 'Modified' : 'Saved'}</span>
        <button onClick={handleSave} className="text-[#555] hover:text-orange-500 transition-colors">
          <i className="fa-solid fa-floppy-disk text-[9px]" /> Save
        </button>
      </div>
    </div>
  );
};

export default ScriptEditor;
