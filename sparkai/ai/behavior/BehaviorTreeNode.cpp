#include "BehaviorTreeNode.h"
#include "Agent.h"

namespace SparkLabs {

BehaviorTreeNode::BehaviorTreeNode()
    : m_NodeType(NodeType::Action)
    , m_Status(NodeStatus::Idle)
    , m_ExecutionCount(0)
{
}

BehaviorTreeNode::BehaviorTreeNode(const String& name, NodeType nodeType)
    : m_NodeType(nodeType)
    , m_Status(NodeStatus::Idle)
    , m_Parent(nullptr)
    , m_Name(name)
    , m_ExecutionCount(0)
{
}

void BehaviorTreeNode::OnChildFinished(BehaviorTreeNode* child, NodeStatus status) {
    if (child && !m_Parent.Expired()) {
        auto parent = m_Parent.Lock();
        if (parent) {
            parent->OnChildFinished(this, status);
        }
    }
}

void BehaviorTreeNode::Reset() {
    m_Status = NodeStatus::Idle;
    for (auto& child : m_Children) {
        child->Reset();
    }
}

void BehaviorTreeNode::AddChild(SmartPtr<BehaviorTreeNode> child) {
    if (child) {
        child->SetParent(WeakPtr<BehaviorTreeNode>(this));
        m_Children.PushBack(child);
    }
}

void BehaviorTreeNode::RemoveChild(BehaviorTreeNode* child) {
    for (size_t i = 0; i < m_Children.Size(); ++i) {
        if (m_Children[i].Get() == child) {
            m_Children[i]->SetStatus(NodeStatus::Idle);
            m_Children.Erase(i);
            return;
        }
    }
}

void BehaviorTreeNode::ClearChildren() {
    for (auto& child : m_Children) {
        child->Reset();
    }
    m_Children.Clear();
}

}
