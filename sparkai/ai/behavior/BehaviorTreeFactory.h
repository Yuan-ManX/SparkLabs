#pragma once

#include "BehaviorTree.h"
#include <map>
#include <functional>

namespace SparkLabs {

class BehaviorTreeFactory {
public:
    using NodeBuilder = std::function<BehaviorTreeNode*()>;

    static BehaviorTreeFactory& GetInstance();

    SmartPtr<BehaviorTreeNode> CreateNode(const String& nodeType);
    SmartPtr<BehaviorTree> CreateTree(const String& treeDefinition);

    void RegisterBuilder(const String& nodeType, NodeBuilder builder);
    void UnregisterBuilder(const String& nodeType);
    bool IsBuilderRegistered(const String& nodeType) const;

    void Clear();

private:
    BehaviorTreeFactory();
    BehaviorTreeFactory(const BehaviorTreeFactory&) = delete;
    BehaviorTreeFactory& operator=(const BehaviorTreeFactory&) = delete;
    ~BehaviorTreeFactory();

    void RegisterDefaultBuilders();

    std::map<String, NodeBuilder> m_Builders;
};

}
