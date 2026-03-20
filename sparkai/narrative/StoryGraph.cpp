#include "StoryGraph.h"

namespace SparkLabs {

StoryGraph::StoryGraph() {
}

StoryGraph::~StoryGraph() {
}

SmartPtr<StoryNode> StoryGraph::GetNode(StringHash id) {
    for (auto& node : m_Nodes) {
        if (node->id == id) {
            return node;
        }
    }
    return nullptr;
}

Vector< SmartPtr<StoryNode> > StoryGraph::GetNextNodes(StringHash currentId) {
    Vector< SmartPtr<StoryNode> > result;
    auto current = GetNode(currentId);
    if (current) {
        for (auto nextId : current->possibleNext) {
            auto next = GetNode(nextId);
            if (next) {
                result.PushBack(next);
            }
        }
    }
    return result;
}

void StoryGraph::AddNode(const StoryNode& node) {
    m_Nodes.PushBack(SmartPtr<StoryNode>(new StoryNode(node)));
}

void StoryGraph::Connect(StringHash from, StringHash to) {
    auto fromNode = GetNode(from);
    if (fromNode) {
        fromNode->possibleNext.PushBack(to);
    }
}

SmartPtr<StoryNode> StoryGraph::Traverse(const StoryDecision& decision) {
    if (decision.availableChoices.Empty()) {
        return nullptr;
    }
    return GetNode(decision.selectedChoice);
}

}
