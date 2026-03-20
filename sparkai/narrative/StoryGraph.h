#ifndef SPARKLABS_ENGINE_NARRATIVE_STORYGRAPH_H
#define SPARKLABS_ENGINE_NARRATIVE_STORYGRAPH_H

#include <Object.h>
#include <SmartPtr.h>
#include <Vector.h>
#include <StringHash.h>

namespace SparkLabs {

struct StoryNode {
    StringHash id;
    StringHash type;
    String content;
    Vector<StringHash> possibleNext;
    Map<StringHash, Variant> properties;
};

struct StoryDecision {
    Vector<StringHash> availableChoices;
    StringHash selectedChoice;
    Vector<String> context;
};

class StoryGraph : public Object {
    SPARKLABS_OBJECT(StoryGraph)
public:
    enum class NodeType {
        Beginning,
        PlotPoint,
        Choice,
        Climax,
        Resolution,
        Branch
    };

    StoryGraph();
    virtual ~StoryGraph();

    SmartPtr<StoryNode> GetNode(StringHash id);
    Vector< SmartPtr<StoryNode> > GetNextNodes(StringHash currentId);

    void AddNode(const StoryNode& node);
    void Connect(StringHash from, StringHash to);

    SmartPtr<StoryNode> Traverse(const StoryDecision& decision);

private:
    Vector< SmartPtr<StoryNode> > m_Nodes;
};

}

#endif
