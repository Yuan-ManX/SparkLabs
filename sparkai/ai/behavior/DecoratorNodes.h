#pragma once

#include "BehaviorTreeNode.h"

namespace SparkLabs {

class Inverter : public BehaviorTreeNode {
public:
    Inverter();
    explicit Inverter(const String& name);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;
};

class Repeater : public BehaviorTreeNode {
public:
    Repeater();
    explicit Repeater(const String& name);
    Repeater(int32 count);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    int32 GetCount() const { return m_Count; }
    void SetCount(int32 count) { m_Count = count; }

private:
    int32 m_Count;
    int32 m_CurrentCount;
};

class Limiter : public BehaviorTreeNode {
public:
    Limiter();
    explicit Limiter(const String& name);
    Limiter(int32 limit);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    int32 GetLimit() const { return m_Limit; }
    void SetLimit(int32 limit) { m_Limit = limit; }

private:
    int32 m_Limit;
    int32 m_ExecutionCount;
};

class UntilSuccess : public BehaviorTreeNode {
public:
    UntilSuccess();
    explicit UntilSuccess(const String& name);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;
};

class UntilFailure : public BehaviorTreeNode {
public:
    UntilFailure();
    explicit UntilFailure(const String& name);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;
};

class TimeLimit : public BehaviorTreeNode {
public:
    TimeLimit();
    explicit TimeLimit(const String& name);
    TimeLimit(float32 timeLimit);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    float32 GetTimeLimit() const { return m_TimeLimit; }
    void SetTimeLimit(float32 timeLimit) { m_TimeLimit = timeLimit; }

private:
    float32 m_TimeLimit;
    float32 m_Elapsed;
};

class RateLimiter : public BehaviorTreeNode {
public:
    RateLimiter();
    explicit RateLimiter(const String& name);
    RateLimiter(float32 minInterval);

    NodeStatus Execute(Agent* agent, float32 deltaTime) override;
    void Reset() override;

    float32 GetMinInterval() const { return m_MinInterval; }
    void SetMinInterval(float32 interval) { m_MinInterval = interval; }

private:
    float32 m_MinInterval;
    float32 m_TimeSinceLastExecution;
};

}
