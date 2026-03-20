#include "WorkflowGraph.h"

namespace SparkLabs {

WorkflowNode::WorkflowNode()
    : m_PosX(0.0f)
    , m_PosY(0.0f)
    , m_Width(200.0f)
    , m_Height(150.0f)
    , m_Muted(false)
    , m_Bypassed(false)
{
}

WorkflowNode::~WorkflowNode() {
}

void WorkflowNode::SetId(const String& id) {
    m_Id = id;
}

String WorkflowNode::GetId() const {
    return m_Id;
}

void WorkflowNode::SetName(const String& name) {
    m_Name = name;
}

String WorkflowNode::GetName() const {
    return m_Name;
}

void WorkflowNode::SetCategory(const String& category) {
    m_Category = category;
}

String WorkflowNode::GetCategory() const {
    return m_Category;
}

void WorkflowNode::SetPosition(float32 x, float32 y) {
    m_PosX = x;
    m_PosY = y;
}

float32 WorkflowNode::GetPosX() const {
    return m_PosX;
}

float32 WorkflowNode::GetPosY() const {
    return m_PosY;
}

void WorkflowNode::SetSize(float32 width, float32 height) {
    m_Width = width;
    m_Height = height;
}

float32 WorkflowNode::GetWidth() const {
    return m_Width;
}

float32 WorkflowNode::GetHeight() const {
    return m_Height;
}

void WorkflowNode::AddInputPin(const PinDefinition& pin) {
    SmartPtr<WorkflowPin> workflowPin = new WorkflowPin();
    workflowPin->SetName(pin.name);
    workflowPin->SetPinType(pin.type);
    workflowPin->SetIsInput(true);
    workflowPin->SetIsOptional(pin.isOptional);
    workflowPin->SetDefaultValue(pin.defaultValue);
    workflowPin->SetValue(pin.defaultValue);
    m_InputPins.PushBack(workflowPin);
}

void WorkflowNode::AddOutputPin(const PinDefinition& pin) {
    SmartPtr<WorkflowPin> workflowPin = new WorkflowPin();
    workflowPin->SetName(pin.name);
    workflowPin->SetPinType(pin.type);
    workflowPin->SetIsInput(false);
    workflowPin->SetDefaultValue(pin.defaultValue);
    workflowPin->SetValue(pin.defaultValue);
    m_OutputPins.PushBack(workflowPin);
}

Vector<SmartPtr<WorkflowPin>> WorkflowNode::GetInputPins() const {
    return m_InputPins;
}

Vector<SmartPtr<WorkflowPin>> WorkflowNode::GetOutputPins() const {
    return m_OutputPins;
}

bool WorkflowNode::Execute(const Map<String, Variant>& inputs, Map<String, Variant>& outputs) {
    return true;
}

void WorkflowNode::OnExecuted() {
}

bool WorkflowNode::IsMuted() const {
    return m_Muted;
}

void WorkflowNode::SetMuted(bool muted) {
    m_Muted = muted;
}

bool WorkflowNode::IsBypassed() const {
    return m_Bypassed;
}

void WorkflowNode::SetBypassed(bool bypassed) {
    m_Bypassed = bypassed;
}

WorkflowPin::WorkflowPin()
    : m_PinType(PinType::Any)
    , m_IsInput(false)
    , m_IsConnected(false)
    , m_IsOptional(false)
{
}

void WorkflowPin::SetName(const String& name) {
    m_Name = name;
}

String WorkflowPin::GetName() const {
    return m_Name;
}

void WorkflowPin::SetPinType(PinType type) {
    m_PinType = type;
}

PinType WorkflowPin::GetPinType() const {
    return m_PinType;
}

void WorkflowPin::SetIsInput(bool isInput) {
    m_IsInput = isInput;
}

bool WorkflowPin::IsInput() const {
    return m_IsInput;
}

void WorkflowPin::SetIsConnected(bool connected) {
    m_IsConnected = connected;
}

bool WorkflowPin::IsConnected() const {
    return m_IsConnected;
}

void WorkflowPin::SetIsOptional(bool optional) {
    m_IsOptional = optional;
}

bool WorkflowPin::IsOptional() const {
    return m_IsOptional;
}

void WorkflowPin::SetDefaultValue(const Variant& value) {
    m_DefaultValue = value;
}

Variant WorkflowPin::GetDefaultValue() const {
    return m_DefaultValue;
}

void WorkflowPin::SetValue(const Variant& value) {
    m_Value = value;
}

Variant WorkflowPin::GetValue() const {
    return m_Value;
}

void WorkflowPin::ConnectTo(WorkflowPin* target) {
    if (target) {
        m_ConnectedPin = target;
        m_IsConnected = true;
    }
}

WorkflowPin* WorkflowPin::GetConnectedPin() const {
    return m_ConnectedPin.Get();
}

WorkflowEdge::WorkflowEdge()
{
}

void WorkflowEdge::SetId(const String& id) {
    m_Id = id;
}

String WorkflowEdge::GetId() const {
    return m_Id;
}

void WorkflowEdge::SetSourceNode(WorkflowNode* node) {
    m_SourceNode = node;
}

WorkflowNode* WorkflowEdge::GetSourceNode() const {
    return m_SourceNode.Get();
}

void WorkflowEdge::SetSourcePin(WorkflowPin* pin) {
    m_SourcePin = pin;
}

WorkflowPin* WorkflowEdge::GetSourcePin() const {
    return m_SourcePin.Get();
}

void WorkflowEdge::SetTargetNode(WorkflowNode* node) {
    m_TargetNode = node;
}

WorkflowNode* WorkflowEdge::GetTargetNode() const {
    return m_TargetNode.Get();
}

void WorkflowEdge::SetTargetPin(WorkflowPin* pin) {
    m_TargetPin = pin;
}

WorkflowPin* WorkflowEdge::GetTargetPin() const {
    return m_TargetPin.Get();
}

WorkflowGraph::WorkflowGraph()
    : m_Executing(false)
{
}

WorkflowGraph::~WorkflowGraph() {
    Clear();
}

void WorkflowGraph::SetName(const String& name) {
    m_Name = name;
}

String WorkflowGraph::GetName() const {
    return m_Name;
}

void WorkflowGraph::AddNode(WorkflowNode* node) {
    if (node && !node->GetId().IsEmpty()) {
        m_Nodes[StringHash(node->GetId())] = node;
    }
}

void WorkflowGraph::RemoveNode(const String& nodeId) {
    m_Nodes.Erase(StringHash(nodeId));
}

WorkflowNode* WorkflowGraph::GetNode(const String& nodeId) const {
    auto it = m_Nodes.Find(StringHash(nodeId));
    if (it != m_Nodes.End()) {
        return it->second.Get();
    }
    return nullptr;
}

Vector<SmartPtr<WorkflowNode>> WorkflowGraph::GetAllNodes() const {
    Vector<SmartPtr<WorkflowNode>> result;
    for (auto& pair : m_Nodes) {
        result.PushBack(pair.second);
    }
    return result;
}

void WorkflowGraph::AddEdge(WorkflowEdge* edge) {
    if (edge && !edge->GetId().IsEmpty()) {
        m_Edges[StringHash(edge->GetId())] = edge;
    }
}

void WorkflowGraph::RemoveEdge(const String& edgeId) {
    m_Edges.Erase(StringHash(edgeId));
}

WorkflowEdge* WorkflowGraph::GetEdge(const String& edgeId) const {
    auto it = m_Edges.Find(StringHash(edgeId));
    if (it != m_Edges.End()) {
        return it->second.Get();
    }
    return nullptr;
}

Vector<SmartPtr<WorkflowEdge>> WorkflowGraph::GetAllEdges() const {
    Vector<SmartPtr<WorkflowEdge>> result;
    for (auto& pair : m_Edges) {
        result.PushBack(pair.second);
    }
    return result;
}

bool WorkflowGraph::CanConnect(WorkflowPin* source, WorkflowPin* target) const {
    if (!source || !target) return false;
    if (source->IsInput() == target->IsInput()) return false;
    if (source->IsInput()) {
        return source->GetPinType() == PinType::Any || target->GetPinType() == PinType::Any ||
               source->GetPinType() == target->GetPinType();
    } else {
        return source->GetPinType() == PinType::Any || target->GetPinType() == PinType::Any ||
               source->GetPinType() == target->GetPinType();
    }
}

bool WorkflowGraph::Connect(WorkflowPin* source, WorkflowPin* target) {
    if (!CanConnect(source, target)) return false;

    if (source->IsInput()) {
        source->ConnectTo(target);
        target->ConnectTo(source);
    } else {
        source->ConnectTo(target);
        target->ConnectTo(source);
    }
    return true;
}

bool WorkflowGraph::Execute() {
    if (m_Executing) return false;
    m_Executing = true;

    for (auto& pair : m_Nodes) {
        WorkflowNode* node = pair.second.Get();
        if (node->IsBypassed()) continue;
        if (node->IsMuted()) continue;

        Map<String, Variant> inputs;
        Map<String, Variant> outputs;

        auto inputPins = node->GetInputPins();
        for (auto& pin : inputPins) {
            if (pin->IsConnected() && pin->GetConnectedPin()) {
                inputs[pin->GetName()] = pin->GetConnectedPin()->GetValue();
            } else if (pin->IsOptional()) {
                inputs[pin->GetName()] = pin->GetDefaultValue();
            }
        }

        if (node->Execute(inputs, outputs)) {
            node->OnExecuted();
            NodeExecutedSignal(node);

            auto outputPins = node->GetOutputPins();
            for (auto& pin : outputPins) {
                auto it = outputs.Find(pin->GetName());
                if (it != outputs.End()) {
                    pin->SetValue(it->second);
                }
            }
        }
    }

    m_Executing = false;
    ExecutionCompletedSignal("");
    return true;
}

void WorkflowGraph::Abort() {
    m_Executing = false;
    ExecutionAbortedSignal();
}

Vector<SmartPtr<WorkflowNode>> WorkflowGraph::GetNodesByCategory(const String& category) const {
    Vector<SmartPtr<WorkflowNode>> result;
    for (auto& pair : m_Nodes) {
        if (pair.second->GetCategory() == category) {
            result.PushBack(pair.second);
        }
    }
    return result;
}

void WorkflowGraph::Clear() {
    m_Nodes.Clear();
    m_Edges.Clear();
}

}
