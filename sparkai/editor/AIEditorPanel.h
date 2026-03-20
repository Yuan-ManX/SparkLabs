#pragma once

#include "../core/Types.h"
#include "../core/string/String.h"
#include "../core/Threading/Signal.h"
#include "../core/memory/SmartPtr.h"

namespace SparkLabs {

class AINode;
class AIBrain;
class BehaviorTree;
class AIMemory;
class EmotionalState;

class AIEditorPanel {
public:
    AIEditorPanel();
    ~AIEditorPanel();

    void ShowAINodeInspector(AINode* node);
    void ShowAIBrainDebugger(AIBrain* brain);
    void ShowBehaviorTreeEditor(BehaviorTree* tree);
    void ShowMemoryVisualizer(AIMemory* memory);
    void ShowEmotionStateEditor(EmotionalState* emotion);

    void Update(float32 deltaTime);
    void Render();

    Signal<void> OnPanelClosed;

private:
    AINode* m_CurrentNode;
    AIBrain* m_CurrentBrain;
    BehaviorTree* m_CurrentTree;
    AIMemory* m_CurrentMemory;
    EmotionalState* m_CurrentEmotion;

    bool m_NodeInspectorVisible;
    bool m_BrainDebuggerVisible;
    bool m_TreeEditorVisible;
    bool m_MemoryVisualizerVisible;
    bool m_EmotionEditorVisible;
};

}
