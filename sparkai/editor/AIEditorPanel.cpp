#include "AIEditorPanel.h"
#include "../ai/brain/AINode.h"
#include "../ai/brain/AIBrain.h"
#include "../ai/behavior/BehaviorTree.h"
#include "../engine/npc/AIMemory.h"
#include "../engine/npc/EmotionalState.h"

namespace SparkLabs {

AIEditorPanel::AIEditorPanel()
    : m_CurrentNode(nullptr)
    , m_CurrentBrain(nullptr)
    , m_CurrentTree(nullptr)
    , m_CurrentMemory(nullptr)
    , m_CurrentEmotion(nullptr)
    , m_NodeInspectorVisible(false)
    , m_BrainDebuggerVisible(false)
    , m_TreeEditorVisible(false)
    , m_MemoryVisualizerVisible(false)
    , m_EmotionEditorVisible(false) {
}

AIEditorPanel::~AIEditorPanel() {
}

void AIEditorPanel::ShowAINodeInspector(AINode* node) {
    m_CurrentNode = node;
    m_NodeInspectorVisible = true;
}

void AIEditorPanel::ShowAIBrainDebugger(AIBrain* brain) {
    m_CurrentBrain = brain;
    m_BrainDebuggerVisible = true;
}

void AIEditorPanel::ShowBehaviorTreeEditor(BehaviorTree* tree) {
    m_CurrentTree = tree;
    m_TreeEditorVisible = true;
}

void AIEditorPanel::ShowMemoryVisualizer(AIMemory* memory) {
    m_CurrentMemory = memory;
    m_MemoryVisualizerVisible = true;
}

void AIEditorPanel::ShowEmotionStateEditor(EmotionalState* emotion) {
    m_CurrentEmotion = emotion;
    m_EmotionEditorVisible = true;
}

void AIEditorPanel::Update(float32 deltaTime) {
    if (m_CurrentNode) {
        m_CurrentNode->OnUpdate(deltaTime);
    }
}

void AIEditorPanel::Render() {
}

}
