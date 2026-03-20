#pragma once

#include "../../../core/Types.h"
#include "../../../core/memory/SmartPtr.h"
#include "../../../core/string/String.h"
#include "../../../core/io/Vector.h"

namespace SparkLabs {

class Agent;

enum class NodeStatus {
    Idle,
    Success,
    Failure,
    Running
};

enum class NodeType {
    Action,
    Composite,
    Decorator,
    Condition
};

class BehaviorTreeNode {
public:
    BehaviorTreeNode();
    BehaviorTreeNode(const String& name, NodeType nodeType);
    virtual ~BehaviorTreeNode() = default;

    virtual NodeStatus Execute(Agent* agent, float32 deltaTime) = 0;
    virtual void OnChildFinished(BehaviorTreeNode* child, NodeStatus status);
    virtual void Reset();

    NodeType GetNodeType() const { return m_NodeType; }
    NodeStatus GetStatus() const { return m_Status; }
    void SetStatus(NodeStatus status) { m_Status = status; }

    const String& GetName() const { return m_Name; }
    void SetName(const String& name) { m_Name = name; }

    int32 GetExecutionCount() const { return m_ExecutionCount; }
    void IncrementExecutionCount() { ++m_ExecutionCount; }
    void ResetExecutionCount() { m_ExecutionCount = 0; }

    WeakPtr<BehaviorTreeNode> GetParent() const { return m_Parent; }
    void SetParent(WeakPtr<BehaviorTreeNode> parent) { m_Parent = parent; }

    const Vector< SmartPtr<BehaviorTreeNode> >& GetChildren() const { return m_Children; }
    void AddChild(SmartPtr<BehaviorTreeNode> child);
    void RemoveChild(BehaviorTreeNode* child);
    void ClearChildren();

    bool IsActive() const { return m_Status == NodeStatus::Running; }
    bool IsIdle() const { return m_Status == NodeStatus::Idle; }
    bool IsSuccess() const { return m_Status == NodeStatus::Success; }
    bool IsFailure() const { return m_Status == NodeStatus::Failure; }

protected:
    NodeType m_NodeType;
    NodeStatus m_Status;
    WeakPtr<BehaviorTreeNode> m_Parent;
    Vector< SmartPtr<BehaviorTreeNode> > m_Children;
    String m_Name;
    int32 m_ExecutionCount;
};

}
