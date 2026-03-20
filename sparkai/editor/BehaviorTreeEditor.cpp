#include "BehaviorTreeEditor.h"
#include "../ai/behavior/BehaviorTree.h"
#include "../ai/behavior/BehaviorTreeNode.h"
#include "../platform/FileSystem.h"

namespace SparkLabs {

BehaviorTreeEditor::BehaviorTreeEditor()
    : m_CurrentTree(nullptr)
    , m_CanvasOffset(0.0f, 0.0f)
    , m_ZoomLevel(1.0f)
    , m_IsDragging(false) {
}

BehaviorTreeEditor::~BehaviorTreeEditor() {
}

void BehaviorTreeEditor::OpenTree(BehaviorTree* tree) {
    m_CurrentTree = tree;
    m_Nodes.Clear();
    m_CanvasOffset = Vector2::Zero;
    m_ZoomLevel = 1.0f;

    if (tree && tree->GetRoot()) {
        m_Nodes.PushBack(tree->GetRoot());
    }
}

void BehaviorTreeEditor::SaveTree(BehaviorTree* tree, const String& path) {
    if (!tree) {
        return;
    }

    FileSystem* fs = FileSystem::GetInstance();
    if (!fs) {
        return;
    }

    String treeData = "BehaviorTreeData";
    fs->WriteAllText(path, treeData);
}

Vector2 BehaviorTreeEditor::ScreenToCanvas(const Vector2& screenPos) {
    return (screenPos - m_CanvasOffset) / m_ZoomLevel;
}

Vector2 BehaviorTreeEditor::CanvasToScreen(const Vector2& canvasPos) {
    return canvasPos * m_ZoomLevel + m_CanvasOffset;
}

void BehaviorTreeEditor::AddNode(BehaviorTreeNode* parent, const Vector2& pos) {
    if (!parent) {
        return;
    }
}

void BehaviorTreeEditor::RemoveNode(BehaviorTreeNode* node) {
    if (!node) {
        return;
    }

    for (size_t i = 0; i < m_Nodes.Size(); ++i) {
        if (m_Nodes[i].Get() == node) {
            m_Nodes.Erase(i);
            return;
        }
    }
}

void BehaviorTreeEditor::ConnectNodes(BehaviorTreeNode* from, BehaviorTreeNode* to) {
    if (!from || !to) {
        return;
    }
}

void BehaviorTreeEditor::Update(float32 deltaTime) {
    if (m_CurrentTree) {
        m_CurrentTree->Execute(deltaTime);
    }
}

void BehaviorTreeEditor::Render() {
}

}
