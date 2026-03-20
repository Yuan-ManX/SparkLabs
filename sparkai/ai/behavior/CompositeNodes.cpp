#include "CompositeNodes.h"
#include "Agent.h"

namespace SparkLabs {

Sequence::Sequence()
    : BehaviorTreeNode("Sequence", NodeType::Composite)
    , m_CurrentChildIndex(0)
{
}

Sequence::Sequence(const String& name)
    : BehaviorTreeNode(name, NodeType::Composite)
    , m_CurrentChildIndex(0)
{
}

NodeStatus Sequence::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Success;
    }

    if (IsIdle()) {
        m_CurrentChildIndex = 0;
        SetStatus(NodeStatus::Running);
    }

    while (m_CurrentChildIndex < static_cast<int32>(m_Children.Size())) {
        NodeStatus childStatus = m_Children[m_CurrentChildIndex]->Execute(agent, deltaTime);

        if (childStatus == NodeStatus::Running) {
            return NodeStatus::Running;
        }

        if (childStatus == NodeStatus::Failure) {
            Reset();
            return NodeStatus::Failure;
        }

        ++m_CurrentChildIndex;
    }

    Reset();
    return NodeStatus::Success;
}

void Sequence::OnChildFinished(BehaviorTreeNode* child, NodeStatus status) {
    if (status == NodeStatus::Failure) {
        Reset();
    } else if (status == NodeStatus::Success) {
        ++m_CurrentChildIndex;
    }
}

void Sequence::Reset() {
    BehaviorTreeNode::Reset();
    m_CurrentChildIndex = 0;
}

Selector::Selector()
    : BehaviorTreeNode("Selector", NodeType::Composite)
    , m_CurrentChildIndex(0)
{
}

Selector::Selector(const String& name)
    : BehaviorTreeNode(name, NodeType::Composite)
    , m_CurrentChildIndex(0)
{
}

NodeStatus Selector::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        m_CurrentChildIndex = 0;
        SetStatus(NodeStatus::Running);
    }

    while (m_CurrentChildIndex < static_cast<int32>(m_Children.Size())) {
        NodeStatus childStatus = m_Children[m_CurrentChildIndex]->Execute(agent, deltaTime);

        if (childStatus == NodeStatus::Running) {
            return NodeStatus::Running;
        }

        if (childStatus == NodeStatus::Success) {
            Reset();
            return NodeStatus::Success;
        }

        ++m_CurrentChildIndex;
    }

    Reset();
    return NodeStatus::Failure;
}

void Selector::OnChildFinished(BehaviorTreeNode* child, NodeStatus status) {
    if (status == NodeStatus::Success) {
        Reset();
    } else if (status == NodeStatus::Failure) {
        ++m_CurrentChildIndex;
    }
}

void Selector::Reset() {
    BehaviorTreeNode::Reset();
    m_CurrentChildIndex = 0;
}

Parallel::Parallel()
    : BehaviorTreeNode("Parallel", NodeType::Composite)
    , m_SuccessThreshold(1)
    , m_FailureThreshold(1)
    , m_SuccessCount(0)
    , m_FailureCount(0)
{
}

Parallel::Parallel(const String& name)
    : BehaviorTreeNode(name, NodeType::Composite)
    , m_SuccessThreshold(1)
    , m_FailureThreshold(1)
    , m_SuccessCount(0)
    , m_FailureCount(0)
{
}

Parallel::Parallel(int32 successThreshold, int32 failureThreshold)
    : BehaviorTreeNode("Parallel", NodeType::Composite)
    , m_SuccessThreshold(successThreshold)
    , m_FailureThreshold(failureThreshold)
    , m_SuccessCount(0)
    , m_FailureCount(0)
{
}

NodeStatus Parallel::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Success;
    }

    if (IsIdle()) {
        m_SuccessCount = 0;
        m_FailureCount = 0;
        SetStatus(NodeStatus::Running);
    }

    for (size_t i = 0; i < m_Children.Size(); ++i) {
        NodeStatus childStatus = m_Children[i]->GetStatus();

        if (childStatus == NodeStatus::Idle) {
            m_Children[i]->SetStatus(NodeStatus::Running);
        }

        if (childStatus != NodeStatus::Running && childStatus != NodeStatus::Idle) {
            continue;
        }

        NodeStatus result = m_Children[i]->Execute(agent, deltaTime);

        if (result == NodeStatus::Success) {
            ++m_SuccessCount;
        } else if (result == NodeStatus::Failure) {
            ++m_FailureCount;
        }
    }

    if (m_FailureCount >= m_FailureThreshold) {
        Reset();
        return NodeStatus::Failure;
    }

    if (m_SuccessCount >= m_SuccessThreshold) {
        Reset();
        return NodeStatus::Success;
    }

    return NodeStatus::Running;
}

void Parallel::OnChildFinished(BehaviorTreeNode* child, NodeStatus status) {
    if (status == NodeStatus::Success) {
        ++m_SuccessCount;
    } else if (status == NodeStatus::Failure) {
        ++m_FailureCount;
    }
}

void Parallel::Reset() {
    BehaviorTreeNode::Reset();
    m_SuccessCount = 0;
    m_FailureCount = 0;
}

RandomSequence::RandomSequence()
    : BehaviorTreeNode("RandomSequence", NodeType::Composite)
    , m_CurrentChildIndex(0)
    , m_CompletedCount(0)
    , m_Initialized(false)
{
}

RandomSequence::RandomSequence(const String& name)
    : BehaviorTreeNode(name, NodeType::Composite)
    , m_CurrentChildIndex(0)
    , m_CompletedCount(0)
    , m_Initialized(false)
{
}

NodeStatus RandomSequence::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Success;
    }

    if (IsIdle()) {
        m_CurrentChildIndex = 0;
        m_CompletedCount = 0;
        m_Initialized = false;
        SetStatus(NodeStatus::Running);
    }

    if (!m_Initialized) {
        m_ExecutionOrder.Resize(m_Children.Size());
        for (size_t i = 0; i < m_Children.Size(); ++i) {
            m_ExecutionOrder[i] = i;
        }
        std::random_device rd;
        std::mt19937 g(rd());
        std::shuffle(m_ExecutionOrder.Begin(), m_ExecutionOrder.End(), g);
        m_Initialized = true;
    }

    while (m_CompletedCount < static_cast<int32>(m_Children.Size())) {
        size_t childIdx = m_ExecutionOrder[m_CurrentChildIndex];
        NodeStatus childStatus = m_Children[childIdx]->Execute(agent, deltaTime);

        if (childStatus == NodeStatus::Running) {
            return NodeStatus::Running;
        }

        if (childStatus == NodeStatus::Failure) {
            Reset();
            return NodeStatus::Failure;
        }

        ++m_CompletedCount;
        ++m_CurrentChildIndex;
    }

    Reset();
    return NodeStatus::Success;
}

void RandomSequence::OnChildFinished(BehaviorTreeNode* child, NodeStatus status) {
    if (status == NodeStatus::Failure) {
        Reset();
    } else if (status == NodeStatus::Success) {
        ++m_CompletedCount;
    }
}

void RandomSequence::Reset() {
    BehaviorTreeNode::Reset();
    m_CurrentChildIndex = 0;
    m_CompletedCount = 0;
    m_Initialized = false;
}

RandomSelector::RandomSelector()
    : BehaviorTreeNode("RandomSelector", NodeType::Composite)
    , m_SelectedChildIndex(0)
    , m_ChildSelected(false)
{
}

RandomSelector::RandomSelector(const String& name)
    : BehaviorTreeNode(name, NodeType::Composite)
    , m_SelectedChildIndex(0)
    , m_ChildSelected(false)
{
}

NodeStatus RandomSelector::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        std::random_device rd;
        std::mt19937 g(rd());
        std::uniform_int_distribution<size_t> dist(0, m_Children.Size() - 1);
        m_SelectedChildIndex = dist(g);
        m_ChildSelected = true;
        SetStatus(NodeStatus::Running);
    }

    if (m_ChildSelected) {
        NodeStatus childStatus = m_Children[m_SelectedChildIndex]->Execute(agent, deltaTime);

        if (childStatus == NodeStatus::Running) {
            return NodeStatus::Running;
        }

        Reset();
        return childStatus;
    }

    return NodeStatus::Failure;
}

void RandomSelector::OnChildFinished(BehaviorTreeNode* child, NodeStatus status) {
    Reset();
}

void RandomSelector::Reset() {
    BehaviorTreeNode::Reset();
    m_ChildSelected = false;
}

}
