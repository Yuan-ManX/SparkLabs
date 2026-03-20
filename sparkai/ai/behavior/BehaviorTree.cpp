#include "BehaviorTree.h"

namespace SparkLabs {

BehaviorTree::BehaviorTree()
    : m_Agent(nullptr)
    , m_Running(false)
{
}

BehaviorTree::~BehaviorTree() {
    Reset();
}

void BehaviorTree::SetRoot(SmartPtr<BehaviorTreeNode> root) {
    m_Root = root;
}

void BehaviorTree::Execute(float32 deltaTime) {
    if (!m_Root || !m_Agent) {
        return;
    }

    m_Running = true;
    Tick(m_Agent, deltaTime);
}

NodeStatus BehaviorTree::Tick(Agent* agent, float32 deltaTime) {
    if (!m_Root || !agent) {
        return NodeStatus::Failure;
    }

    return m_Root->Execute(agent, deltaTime);
}

void BehaviorTree::Reset() {
    if (m_Root) {
        m_Root->Reset();
    }
    m_Running = false;
}

}
