#ifndef SPARKLABS_SPARKAI_WORKFLOW_WORKFLOWGRAPH_H
#define SPARKLABS_SPARKAI_WORKFLOW_WORKFLOWGRAPH_H

#include <Object.h>
#include <SmartPtr.h>
#include <Vector.h>
#include <String.h>
#include <StringHash.h>
#include <Map.h>

namespace SparkLabs {

class WorkflowNode;
class WorkflowEdge;
class WorkflowPin;

enum class PinType {
    Any,
    Image,
    Video,
    Audio,
    Text,
    Model,
    Number,
    Boolean,
    Trigger
};

struct PinDefinition {
    String name;
    PinType type;
    bool isInput;
    bool isOptional;
    Variant defaultValue;
};

class WorkflowNode : public Object {
    SPARKLABS_OBJECT(WorkflowNode)
public:
    WorkflowNode();
    virtual ~WorkflowNode();

    void SetId(const String& id);
    String GetId() const;

    void SetName(const String& name);
    String GetName() const;

    void SetCategory(const String& category);
    String GetCategory() const;

    void SetPosition(float32 x, float32 y);
    float32 GetPosX() const;
    float32 GetPosY() const;

    void SetSize(float32 width, float32 height);
    float32 GetWidth() const;
    float32 GetHeight() const;

    void AddInputPin(const PinDefinition& pin);
    void AddOutputPin(const PinDefinition& pin);
    Vector<SmartPtr<WorkflowPin>> GetInputPins() const;
    Vector<SmartPtr<WorkflowPin>> GetOutputPins() const;

    virtual bool Execute(const Map<String, Variant>& inputs, Map<String, Variant>& outputs);
    virtual void OnExecuted();

    bool IsMuted() const;
    void SetMuted(bool muted);

    bool IsBypassed() const;
    void SetBypassed(bool bypassed);

protected:
    String m_Id;
    String m_Name;
    String m_Category;
    float32 m_PosX;
    float32 m_PosY;
    float32 m_Width;
    float32 m_Height;
    Vector<SmartPtr<WorkflowPin>> m_InputPins;
    Vector<SmartPtr<WorkflowPin>> m_OutputPins;
    bool m_Muted;
    bool m_Bypassed;
};

class WorkflowPin : public Object {
    SPARKLABS_OBJECT(WorkflowPin)
public:
    WorkflowPin();

    void SetName(const String& name);
    String GetName() const;

    void SetPinType(PinType type);
    PinType GetPinType() const;

    void SetIsInput(bool isInput);
    bool IsInput() const;

    void SetIsConnected(bool connected);
    bool IsConnected() const;

    void SetIsOptional(bool optional);
    bool IsOptional() const;

    void SetDefaultValue(const Variant& value);
    Variant GetDefaultValue() const;

    void SetValue(const Variant& value);
    Variant GetValue() const;

    void ConnectTo(WorkflowPin* target);
    WorkflowPin* GetConnectedPin() const;

private:
    String m_Name;
    PinType m_PinType;
    bool m_IsInput;
    bool m_IsConnected;
    bool m_IsOptional;
    Variant m_DefaultValue;
    Variant m_Value;
    WeakPtr<WorkflowPin> m_ConnectedPin;
};

class WorkflowEdge : public Object {
    SPARKLABS_OBJECT(WorkflowEdge)
public:
    WorkflowEdge();

    void SetId(const String& id);
    String GetId() const;

    void SetSourceNode(WorkflowNode* node);
    WorkflowNode* GetSourceNode() const;

    void SetSourcePin(WorkflowPin* pin);
    WorkflowPin* GetSourcePin() const;

    void SetTargetNode(WorkflowNode* node);
    WorkflowNode* GetTargetNode() const;

    void SetTargetPin(WorkflowPin* pin);
    WorkflowPin* GetTargetPin() const;

private:
    String m_Id;
    WeakPtr<WorkflowNode> m_SourceNode;
    WeakPtr<WorkflowPin> m_SourcePin;
    WeakPtr<WorkflowNode> m_TargetNode;
    WeakPtr<WorkflowPin> m_TargetPin;
};

class WorkflowGraph : public Object {
    SPARKLABS_OBJECT(WorkflowGraph)
public:
    WorkflowGraph();
    virtual ~WorkflowGraph();

    void SetName(const String& name);
    String GetName() const;

    void AddNode(WorkflowNode* node);
    void RemoveNode(const String& nodeId);
    WorkflowNode* GetNode(const String& nodeId) const;
    Vector<SmartPtr<WorkflowNode>> GetAllNodes() const;

    void AddEdge(WorkflowEdge* edge);
    void RemoveEdge(const String& edgeId);
    WorkflowEdge* GetEdge(const String& edgeId) const;
    Vector<SmartPtr<WorkflowEdge>> GetAllEdges() const;

    bool CanConnect(WorkflowPin* source, WorkflowPin* target) const;
    bool Connect(WorkflowPin* source, WorkflowPin* target);

    bool Execute();
    void Abort();

    Vector<SmartPtr<WorkflowNode>> GetNodesByCategory(const String& category) const;

    void Clear();

    Signal<void(WorkflowNode*)> NodeExecutedSignal;
    Signal<void(const String&)> ExecutionCompletedSignal;
    Signal<void()> ExecutionAbortedSignal;

private:
    String m_Name;
    Map<StringHash, SmartPtr<WorkflowNode>> m_Nodes;
    Map<StringHash, SmartPtr<WorkflowEdge>> m_Edges;
    bool m_Executing;
};

}

#endif
