#include "ActionNodes.h"
#include "Agent.h"

namespace SparkLabs {

WaitAction::WaitAction()
    : BehaviorTreeNode("WaitAction", NodeType::Action)
    , m_Duration(1.0f)
    , m_Elapsed(0.0f)
{
}

WaitAction::WaitAction(const String& name)
    : BehaviorTreeNode(name, NodeType::Action)
    , m_Duration(1.0f)
    , m_Elapsed(0.0f)
{
}

WaitAction::WaitAction(float32 duration)
    : BehaviorTreeNode("WaitAction", NodeType::Action)
    , m_Duration(duration)
    , m_Elapsed(0.0f)
{
}

NodeStatus WaitAction::Execute(Agent* agent, float32 deltaTime) {
    if (IsIdle()) {
        m_Elapsed = 0.0f;
        SetStatus(NodeStatus::Running);
    }

    m_Elapsed += deltaTime;

    if (m_Elapsed >= m_Duration) {
        Reset();
        return NodeStatus::Success;
    }

    return NodeStatus::Running;
}

void WaitAction::Reset() {
    BehaviorTreeNode::Reset();
    m_Elapsed = 0.0f;
}

ConditionAction::ConditionAction()
    : BehaviorTreeNode("ConditionAction", NodeType::Condition)
{
}

ConditionAction::ConditionAction(const String& name)
    : BehaviorTreeNode(name, NodeType::Condition)
{
}

ConditionAction::ConditionAction(std::function<bool()> condition)
    : BehaviorTreeNode("ConditionAction", NodeType::Condition)
    , m_Condition(condition)
{
}

NodeStatus ConditionAction::Execute(Agent* agent, float32 deltaTime) {
    if (!m_Condition) {
        return NodeStatus::Failure;
    }

    if (m_Condition()) {
        return NodeStatus::Success;
    }

    return NodeStatus::Failure;
}

void ConditionAction::Reset() {
    BehaviorTreeNode::Reset();
}

ExecuteScriptAction::ExecuteScriptAction()
    : BehaviorTreeNode("ExecuteScriptAction", NodeType::Action)
{
}

ExecuteScriptAction::ExecuteScriptAction(const String& name)
    : BehaviorTreeNode(name, NodeType::Action)
{
}

ExecuteScriptAction::ExecuteScriptAction(const String& name, const String& scriptPath)
    : BehaviorTreeNode(name, NodeType::Action)
    , m_ScriptPath(scriptPath)
{
}

NodeStatus ExecuteScriptAction::Execute(Agent* agent, float32 deltaTime) {
    if (m_ScriptPath.Empty()) {
        return NodeStatus::Failure;
    }

    SetStatus(NodeStatus::Running);
    Reset();
    return NodeStatus::Success;
}

void ExecuteScriptAction::Reset() {
    BehaviorTreeNode::Reset();
}

MoveToAction::MoveToAction()
    : BehaviorTreeNode("MoveToAction", NodeType::Action)
    , m_Moving(false)
{
}

MoveToAction::MoveToAction(const String& name)
    : BehaviorTreeNode(name, NodeType::Action)
    , m_Moving(false)
{
}

MoveToAction::MoveToAction(const String& name, const Vector3& targetPosition)
    : BehaviorTreeNode(name, NodeType::Action)
    , m_TargetPosition(targetPosition)
    , m_Moving(false)
{
}

NodeStatus MoveToAction::Execute(Agent* agent, float32 deltaTime) {
    if (IsIdle()) {
        m_Moving = true;
        SetStatus(NodeStatus::Running);
    }

    if (!m_Moving) {
        return NodeStatus::Failure;
    }

    Vector3 currentPos = agent->GetPosition();
    float32 distance = Vector3::Distance(currentPos, m_TargetPosition);

    if (distance < 0.1f) {
        m_Moving = false;
        Reset();
        return NodeStatus::Success;
    }

    return NodeStatus::Running;
}

void MoveToAction::Reset() {
    BehaviorTreeNode::Reset();
    m_Moving = false;
}

AttackAction::AttackAction()
    : BehaviorTreeNode("AttackAction", NodeType::Action)
    , m_Attacking(false)
{
}

AttackAction::AttackAction(const String& name)
    : BehaviorTreeNode(name, NodeType::Action)
    , m_Attacking(false)
{
}

NodeStatus AttackAction::Execute(Agent* agent, float32 deltaTime) {
    if (IsIdle()) {
        m_Attacking = true;
        SetStatus(NodeStatus::Running);
    }

    if (m_Attacking) {
        m_Attacking = false;
        Reset();
        return NodeStatus::Success;
    }

    return NodeStatus::Running;
}

void AttackAction::Reset() {
    BehaviorTreeNode::Reset();
    m_Attacking = false;
}

PatrolAction::PatrolAction()
    : BehaviorTreeNode("PatrolAction", NodeType::Action)
    , m_CurrentWaypointIndex(0)
    , m_Patrolling(false)
{
}

PatrolAction::PatrolAction(const String& name)
    : BehaviorTreeNode(name, NodeType::Action)
    , m_CurrentWaypointIndex(0)
    , m_Patrolling(false)
{
}

NodeStatus PatrolAction::Execute(Agent* agent, float32 deltaTime) {
    if (m_Waypoints.Empty()) {
        return NodeStatus::Failure;
    }

    if (IsIdle()) {
        m_CurrentWaypointIndex = 0;
        m_Patrolling = true;
        SetStatus(NodeStatus::Running);
    }

    if (!m_Patrolling) {
        return NodeStatus::Failure;
    }

    Vector3 currentPos = agent->GetPosition();
    const Vector3& targetWaypoint = m_Waypoints[m_CurrentWaypointIndex];
    float32 distance = Vector3::Distance(currentPos, targetWaypoint);

    if (distance < 0.1f) {
        ++m_CurrentWaypointIndex;
        if (m_CurrentWaypointIndex >= static_cast<int32>(m_Waypoints.Size())) {
            m_CurrentWaypointIndex = 0;
        }
        return NodeStatus::Running;
    }

    return NodeStatus::Running;
}

void PatrolAction::Reset() {
    BehaviorTreeNode::Reset();
    m_CurrentWaypointIndex = 0;
    m_Patrolling = false;
}

void PatrolAction::AddWaypoint(const Vector3& waypoint) {
    m_Waypoints.PushBack(waypoint);
}

}
