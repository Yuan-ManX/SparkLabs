#ifndef SPARKLABS_SPARKAI_WORKFLOW_WORKFLOWFACTORY_H
#define SPARKLABS_SPARKAI_WORKFLOW_WORKFLOWFACTORY_H

#include "WorkflowGraph.h"
#include <Map.h>
#include <Vector.h>
#include <String.h>

namespace SparkLabs {

class WorkflowNodeRegistry {
public:
    using NodeCreator = std::function<WorkflowNode*()>;

    static WorkflowNodeRegistry& GetInstance();

    void RegisterNode(const String& category, const String& name, NodeCreator creator);
    WorkflowNode* CreateNode(const String& category, const String& name);
    Vector<String> GetCategories() const;
    Vector<String> GetNodeNames(const String& category) const;
    Vector< Pair<String, String> > GetAllNodes() const;

private:
    WorkflowNodeRegistry() = default;
    Map<String, Map<String, NodeCreator>> m_Registry;
};

class WorkflowSerializer {
public:
    static String Serialize(const WorkflowGraph* graph);
    static SmartPtr<WorkflowGraph> Deserialize(const String& json);

    static String SerializeNode(const WorkflowNode* node);
    static SmartPtr<WorkflowNode> DeserializeNode(const String& json);

    static String SerializeEdge(const WorkflowEdge* edge);
    static SmartPtr<WorkflowEdge> DeserializeEdge(const String& json);
};

class WorkflowExecutor {
public:
    WorkflowExecutor();
    ~WorkflowExecutor();

    void SetGraph(WorkflowGraph* graph);
    WorkflowGraph* GetGraph() const;

    bool Execute();
    void Abort();

    bool IsExecuting() const;
    float32 GetProgress() const;

    void SetExecutionCallback(std::function<void(WorkflowNode*)> callback);

private:
    bool ExecuteNode(WorkflowNode* node);
    Map<String, Variant> CollectInputs(WorkflowNode* node);
    void DistributeOutputs(WorkflowNode* node, const Map<String, Variant>& outputs);

    WorkflowGraph* m_Graph;
    bool m_Executing;
    float32 m_Progress;
    std::function<void(WorkflowNode*)> m_Callback;
};

class WorkflowHistory {
public:
    void SaveState(const WorkflowGraph* graph);
    bool Undo();
    bool Redo();
    bool CanUndo() const;
    bool CanRedo() const;

private:
    Vector<String> m_UndoStack;
    Vector<String> m_RedoStack;
};

}

#endif
