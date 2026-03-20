#pragma once

#include "../core/Types.h"
#include "../core/string/String.h"
#include "../core/math/Vector2.h"
#include "../core/memory/SmartPtr.h"
#include "../core/io/Vector.h"

namespace SparkLabs {

class BehaviorTree;
class BehaviorTreeNode;

class BehaviorTreeEditor {
public:
    BehaviorTreeEditor();
    ~BehaviorTreeEditor();

    void OpenTree(BehaviorTree* tree);
    void SaveTree(BehaviorTree* tree, const String& path);

    Vector2 ScreenToCanvas(const Vector2& screenPos);
    Vector2 CanvasToScreen(const Vector2& canvasPos);

    void AddNode(BehaviorTreeNode* parent, const Vector2& pos);
    void RemoveNode(BehaviorTreeNode* node);
    void ConnectNodes(BehaviorTreeNode* from, BehaviorTreeNode* to);

    void Update(float32 deltaTime);
    void Render();

    BehaviorTree* GetCurrentTree() const { return m_CurrentTree; }

private:
    BehaviorTree* m_CurrentTree;
    Vector< SmartPtr<BehaviorTreeNode> > m_Nodes;
    Vector2 m_CanvasOffset;
    float32 m_ZoomLevel;
    Vector2 m_DragStart;
    bool m_IsDragging;
};

}
