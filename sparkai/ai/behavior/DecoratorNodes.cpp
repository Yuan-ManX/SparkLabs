#include "DecoratorNodes.h"
#include "Agent.h"

namespace SparkLabs {

Inverter::Inverter()
    : BehaviorTreeNode("Inverter", NodeType::Decorator)
{
}

Inverter::Inverter(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
{
}

NodeStatus Inverter::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    switch (childStatus) {
        case NodeStatus::Success:
            return NodeStatus::Failure;
        case NodeStatus::Failure:
            return NodeStatus::Success;
        default:
            return childStatus;
    }
}

void Inverter::Reset() {
    BehaviorTreeNode::Reset();
}

Repeater::Repeater()
    : BehaviorTreeNode("Repeater", NodeType::Decorator)
    , m_Count(-1)
    , m_CurrentCount(0)
{
}

Repeater::Repeater(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
    , m_Count(-1)
    , m_CurrentCount(0)
{
}

Repeater::Repeater(int32 count)
    : BehaviorTreeNode("Repeater", NodeType::Decorator)
    , m_Count(count)
    , m_CurrentCount(0)
{
}

NodeStatus Repeater::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Success;
    }

    if (IsIdle()) {
        m_CurrentCount = 0;
        SetStatus(NodeStatus::Running);
    }

    if (m_Count > 0 && m_CurrentCount >= m_Count) {
        Reset();
        return NodeStatus::Success;
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    if (childStatus == NodeStatus::Running) {
        return NodeStatus::Running;
    }

    if (childStatus == NodeStatus::Success || childStatus == NodeStatus::Failure) {
        m_Children[0]->Reset();
        ++m_CurrentCount;

        if (m_Count > 0 && m_CurrentCount >= m_Count) {
            Reset();
            return NodeStatus::Success;
        }

        return NodeStatus::Running;
    }

    return NodeStatus::Failure;
}

void Repeater::Reset() {
    BehaviorTreeNode::Reset();
    m_CurrentCount = 0;
}

Limiter::Limiter()
    : BehaviorTreeNode("Limiter", NodeType::Decorator)
    , m_Limit(1)
    , m_ExecutionCount(0)
{
}

Limiter::Limiter(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
    , m_Limit(1)
    , m_ExecutionCount(0)
{
}

Limiter::Limiter(int32 limit)
    : BehaviorTreeNode("Limiter", NodeType::Decorator)
    , m_Limit(limit)
    , m_ExecutionCount(0)
{
}

NodeStatus Limiter::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (m_ExecutionCount >= m_Limit) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        SetStatus(NodeStatus::Running);
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    if (childStatus != NodeStatus::Running) {
        ++m_ExecutionCount;
        Reset();
    }

    return childStatus;
}

void Limiter::Reset() {
    BehaviorTreeNode::Reset();
}

UntilSuccess::UntilSuccess()
    : BehaviorTreeNode("UntilSuccess", NodeType::Decorator)
{
}

UntilSuccess::UntilSuccess(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
{
}

NodeStatus UntilSuccess::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        SetStatus(NodeStatus::Running);
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    if (childStatus == NodeStatus::Running) {
        return NodeStatus::Running;
    }

    if (childStatus == NodeStatus::Success) {
        Reset();
        return NodeStatus::Success;
    }

    m_Children[0]->Reset();
    return NodeStatus::Running;
}

void UntilSuccess::Reset() {
    BehaviorTreeNode::Reset();
}

UntilFailure::UntilFailure()
    : BehaviorTreeNode("UntilFailure", NodeType::Decorator)
{
}

UntilFailure::UntilFailure(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
{
}

NodeStatus UntilFailure::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        SetStatus(NodeStatus::Running);
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    if (childStatus == NodeStatus::Running) {
        return NodeStatus::Running;
    }

    if (childStatus == NodeStatus::Failure) {
        Reset();
        return NodeStatus::Success;
    }

    m_Children[0]->Reset();
    return NodeStatus::Running;
}

void UntilFailure::Reset() {
    BehaviorTreeNode::Reset();
}

TimeLimit::TimeLimit()
    : BehaviorTreeNode("TimeLimit", NodeType::Decorator)
    , m_TimeLimit(1.0f)
    , m_Elapsed(0.0f)
{
}

TimeLimit::TimeLimit(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
    , m_TimeLimit(1.0f)
    , m_Elapsed(0.0f)
{
}

TimeLimit::TimeLimit(float32 timeLimit)
    : BehaviorTreeNode("TimeLimit", NodeType::Decorator)
    , m_TimeLimit(timeLimit)
    , m_Elapsed(0.0f)
{
}

NodeStatus TimeLimit::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        m_Elapsed = 0.0f;
        SetStatus(NodeStatus::Running);
    }

    m_Elapsed += deltaTime;

    if (m_Elapsed >= m_TimeLimit) {
        Reset();
        return NodeStatus::Failure;
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    if (childStatus != NodeStatus::Running) {
        Reset();
    }

    return childStatus;
}

void TimeLimit::Reset() {
    BehaviorTreeNode::Reset();
    m_Elapsed = 0.0f;
}

RateLimiter::RateLimiter()
    : BehaviorTreeNode("RateLimiter", NodeType::Decorator)
    , m_MinInterval(1.0f)
    , m_TimeSinceLastExecution(0.0f)
{
}

RateLimiter::RateLimiter(const String& name)
    : BehaviorTreeNode(name, NodeType::Decorator)
    , m_MinInterval(1.0f)
    , m_TimeSinceLastExecution(0.0f)
{
}

RateLimiter::RateLimiter(float32 minInterval)
    : BehaviorTreeNode("RateLimiter", NodeType::Decorator)
    , m_MinInterval(minInterval)
    , m_TimeSinceLastExecution(0.0f)
{
}

NodeStatus RateLimiter::Execute(Agent* agent, float32 deltaTime) {
    if (m_Children.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        m_TimeSinceLastExecution = 0.0f;
        SetStatus(NodeStatus::Running);
    }

    m_TimeSinceLastExecution += deltaTime;

    if (m_TimeSinceLastExecution < m_MinInterval) {
        return NodeStatus::Failure;
    }

    NodeStatus childStatus = m_Children[0]->Execute(agent, deltaTime);

    if (childStatus != NodeStatus::Running) {
        m_TimeSinceLastExecution = 0.0f;
        Reset();
    }

    return childStatus;
}

void RateLimiter::Reset() {
    BehaviorTreeNode::Reset();
    m_TimeSinceLastExecution = 0.0f;
}

}
