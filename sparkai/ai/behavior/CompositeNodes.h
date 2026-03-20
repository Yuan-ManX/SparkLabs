#pragma once

#include "BehaviorTreeNode.h"
#include <algorithm>
#include <random>

namespace SparkLabs {

class Sequence : public BehaviorTreeNode {
public:
    Sequence();
    explicit Sequence(const String& name);

    NodeStatus Execute(Agent* agent) override;
    void OnChildFinished(BehaviorTreeNode* child, NodeStatus status) override;
    void Reset() override;

private:
    int32 m_CurrentChildIndex;
};

class Selector : public BehaviorTreeNode {
public:
    Selector();
    explicit Selector(const String& name);

    NodeStatus Execute(Agent* agent) override;
    void OnChildFinished(BehaviorTreeNode* child, NodeStatus status) override;
    void Reset() override;

private:
    int32 m_CurrentChildIndex;
};

class Parallel : public BehaviorTreeNode {
public:
    Parallel();
    explicit Parallel(const String& name);
    Parallel(int32 successThreshold, int32 failureThreshold);

    NodeStatus Execute(Agent* agent) override;
    void OnChildFinished(BehaviorTreeNode* child, NodeStatus status) override;
    void Reset() override;

    int32 GetSuccessThreshold() const { return m_SuccessThreshold; }
    void SetSuccessThreshold(int32 threshold) { m_SuccessThreshold = threshold; }

    int32 GetFailureThreshold() const { return m_FailureThreshold; }
    void SetFailureThreshold(int32 threshold) { m_FailureThreshold = threshold; }

private:
    int32 m_SuccessThreshold;
    int32 m_FailureThreshold;
    int32 m_SuccessCount;
    int32 m_FailureCount;
};

class RandomSequence : public BehaviorTreeNode {
public:
    RandomSequence();
    explicit RandomSequence(const String& name);

    NodeStatus Execute(Agent* agent) override;
    void OnChildFinished(BehaviorTreeNode* child, NodeStatus status) override;
    void Reset() override;

private:
    Vector<size_t> m_ExecutionOrder;
    int32 m_CurrentChildIndex;
    int32 m_CompletedCount;
    bool m_Initialized;
};

class RandomSelector : public BehaviorTreeNode {
public:
    RandomSelector();
    explicit RandomSelector(const String& name);

    NodeStatus Execute(Agent* agent) override;
    void OnChildFinished(BehaviorTreeNode* child, NodeStatus status) override;
    void Reset() override;

private:
    size_t m_SelectedChildIndex;
    bool m_ChildSelected;
};

}
