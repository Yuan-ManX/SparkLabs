#pragma once

#include "BehaviorTreeNode.h"

namespace SparkLabs {

class BehaviorTree {
public:
    BehaviorTree();
    ~BehaviorTree();

    SmartPtr<BehaviorTreeNode> GetRoot() const { return m_Root; }
    void SetRoot(SmartPtr<BehaviorTreeNode> root);

    Agent* GetAgent() const { return m_Agent; }
    void SetAgent(Agent* agent) { m_Agent = agent; }

    void Execute(float32 deltaTime);
    void Reset();
    NodeStatus Tick(Agent* agent, float32 deltaTime);

    bool IsRunning() const { return m_Running; }
    void Stop() { m_Running = false; }

private:
    SmartPtr<BehaviorTreeNode> m_Root;
    Agent* m_Agent;
    bool m_Running;
};

}
