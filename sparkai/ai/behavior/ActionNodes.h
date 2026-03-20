#pragma once

#include "BehaviorTreeNode.h"
#include "../../../core/math/Vector3.h"
#include <functional>

namespace SparkLabs {

class WaitAction : public BehaviorTreeNode {
public:
    WaitAction();
    explicit WaitAction(const String& name);
    WaitAction(float32 duration);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    float32 GetDuration() const { return m_Duration; }
    void SetDuration(float32 duration) { m_Duration = duration; }

private:
    float32 m_Duration;
    float32 m_Elapsed;
};

class ConditionAction : public BehaviorTreeNode {
public:
    ConditionAction();
    explicit ConditionAction(const String& name);
    ConditionAction(std::function<bool()> condition);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    void SetCondition(std::function<bool()> condition) { m_Condition = condition; }

private:
    std::function<bool()> m_Condition;
};

class ExecuteScriptAction : public BehaviorTreeNode {
public:
    ExecuteScriptAction();
    explicit ExecuteScriptAction(const String& name);
    ExecuteScriptAction(const String& name, const String& scriptPath);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    const String& GetScriptPath() const { return m_ScriptPath; }
    void SetScriptPath(const String& path) { m_ScriptPath = path; }

private:
    String m_ScriptPath;
};

class MoveToAction : public BehaviorTreeNode {
public:
    MoveToAction();
    explicit MoveToAction(const String& name);
    MoveToAction(const String& name, const Vector3& targetPosition);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    const Vector3& GetTargetPosition() const { return m_TargetPosition; }
    void SetTargetPosition(const Vector3& position) { m_TargetPosition = position; }

private:
    Vector3 m_TargetPosition;
    bool m_Moving;
};

class AttackAction : public BehaviorTreeNode {
public:
    AttackAction();
    explicit AttackAction(const String& name);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

private:
    bool m_Attacking;
};

class PatrolAction : public BehaviorTreeNode {
public:
    PatrolAction();
    explicit PatrolAction(const String& name);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    void AddWaypoint(const Vector3& waypoint);
    const Vector< Vector3 >& GetWaypoints() const { return m_Waypoints; }
    void ClearWaypoints() { m_Waypoints.Clear(); }

private:
    Vector< Vector3 > m_Waypoints;
    int32 m_CurrentWaypointIndex;
    bool m_Patrolling;
};

}
