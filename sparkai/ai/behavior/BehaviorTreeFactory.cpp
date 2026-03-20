#include "BehaviorTreeFactory.h"
#include "CompositeNodes.h"
#include "DecoratorNodes.h"
#include "ActionNodes.h"

namespace SparkLabs {

BehaviorTreeFactory::BehaviorTreeFactory() {
    RegisterDefaultBuilders();
}

BehaviorTreeFactory::~BehaviorTreeFactory() {
    Clear();
}

BehaviorTreeFactory& BehaviorTreeFactory::GetInstance() {
    static BehaviorTreeFactory instance;
    return instance;
}

void BehaviorTreeFactory::RegisterDefaultBuilders() {
    m_Builders["Sequence"] = []() -> BehaviorTreeNode* { return new Sequence(); };
    m_Builders["Selector"] = []() -> BehaviorTreeNode* { return new Selector(); };
    m_Builders["Parallel"] = []() -> BehaviorTreeNode* { return new Parallel(); };
    m_Builders["RandomSequence"] = []() -> BehaviorTreeNode* { return new RandomSequence(); };
    m_Builders["RandomSelector"] = []() -> BehaviorTreeNode* { return new RandomSelector(); };

    m_Builders["Inverter"] = []() -> BehaviorTreeNode* { return new Inverter(); };
    m_Builders["Repeater"] = []() -> BehaviorTreeNode* { return new Repeater(); };
    m_Builders["Limiter"] = []() -> BehaviorTreeNode* { return new Limiter(); };
    m_Builders["UntilSuccess"] = []() -> BehaviorTreeNode* { return new UntilSuccess(); };
    m_Builders["UntilFailure"] = []() -> BehaviorTreeNode* { return new UntilFailure(); };
    m_Builders["TimeLimit"] = []() -> BehaviorTreeNode* { return new TimeLimit(); };
    m_Builders["RateLimiter"] = []() -> BehaviorTreeNode* { return new RateLimiter(); };

    m_Builders["WaitAction"] = []() -> BehaviorTreeNode* { return new WaitAction(); };
    m_Builders["ConditionAction"] = []() -> BehaviorTreeNode* { return new ConditionAction(); };
    m_Builders["ExecuteScriptAction"] = []() -> BehaviorTreeNode* { return new ExecuteScriptAction(); };
    m_Builders["MoveToAction"] = []() -> BehaviorTreeNode* { return new MoveToAction(); };
    m_Builders["AttackAction"] = []() -> BehaviorTreeNode* { return new AttackAction(); };
    m_Builders["PatrolAction"] = []() -> BehaviorTreeNode* { return new PatrolAction(); };
}

SmartPtr<BehaviorTreeNode> BehaviorTreeFactory::CreateNode(const String& nodeType) {
    auto it = m_Builders.find(nodeType);
    if (it != m_Builders.end()) {
        return SmartPtr<BehaviorTreeNode>(it->second());
    }
    return SmartPtr<BehaviorTreeNode>(nullptr);
}

SmartPtr<BehaviorTree> BehaviorTreeFactory::CreateTree(const String& treeDefinition) {
    SmartPtr<BehaviorTree> tree = MakeSmartPtr<BehaviorTree>();
    return tree;
}

void BehaviorTreeFactory::RegisterBuilder(const String& nodeType, NodeBuilder builder) {
    m_Builders[nodeType] = builder;
}

void BehaviorTreeFactory::UnregisterBuilder(const String& nodeType) {
    auto it = m_Builders.find(nodeType);
    if (it != m_Builders.end()) {
        m_Builders.erase(it);
    }
}

bool BehaviorTreeFactory::IsBuilderRegistered(const String& nodeType) const {
    return m_Builders.find(nodeType) != m_Builders.end();
}

void BehaviorTreeFactory::Clear() {
    m_Builders.clear();
}

}
