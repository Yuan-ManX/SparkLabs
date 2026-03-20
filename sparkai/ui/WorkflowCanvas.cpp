#include "WorkflowCanvas.h"

namespace SparkLabs {

WorkflowCanvas::WorkflowCanvas()
    : m_Graph(nullptr)
    , m_Zoom(1.0f)
    , m_PanX(0.0f)
    , m_PanY(0.0f)
    , m_Dirty(true)
{
}

WorkflowCanvas::~WorkflowCanvas() {
}

void WorkflowCanvas::SetGraph(WorkflowGraph* graph) {
    m_Graph = graph;
}

WorkflowGraph* WorkflowCanvas::GetGraph() const {
    return m_Graph;
}

void WorkflowCanvas::SetZoom(float32 zoom) {
    m_Zoom = Math::Clamp(zoom, 0.1f, 5.0f);
}

float32 WorkflowCanvas::GetZoom() const {
    return m_Zoom;
}

void WorkflowCanvas::SetPan(float32 x, float32 y) {
    m_PanX = x;
    m_PanY = y;
}

float32 WorkflowCanvas::GetPanX() const {
    return m_PanX;
}

float32 WorkflowCanvas::GetPanY() const {
    return m_PanY;
}

void WorkflowCanvas::AddNode(WorkflowNode* node, float32 x, float32 y) {
    if (!node || !m_Graph) return;

    node->SetPosition(x, y);
    m_Graph->AddNode(node);
    m_Dirty = true;
}

void WorkflowCanvas::RemoveNode(const String& nodeId) {
    if (!m_Graph) return;

    m_Graph->RemoveNode(nodeId);
    for (auto it = m_SelectedNodes.Begin(); it != m_SelectedNodes.End(); ++it) {
        if (*it == nodeId) {
            m_SelectedNodes.Erase(it);
            break;
        }
    }
    m_Dirty = true;
}

void WorkflowCanvas::Connect(const String& sourceNodeId, int32 sourcePin, const String& targetNodeId, int32 targetPin) {
}

void WorkflowCanvas::Disconnect(const String& edgeId) {
    if (!m_Graph) return;
    m_Graph->RemoveEdge(edgeId);
    m_Dirty = true;
}

void WorkflowCanvas::SelectNode(const String& nodeId) {
    m_SelectedNodes.Clear();
    m_SelectedNodes.PushBack(nodeId);
}

void WorkflowCanvas::SelectNodes(const Vector<String>& nodeIds) {
    m_SelectedNodes = nodeIds;
}

void WorkflowCanvas::ClearSelection() {
    m_SelectedNodes.Clear();
}

Vector<String> WorkflowCanvas::GetSelectedNodes() const {
    return m_SelectedNodes;
}

void WorkflowCanvas::MoveNode(const String& nodeId, float32 x, float32 y) {
    if (!m_Graph) return;

    WorkflowNode* node = m_Graph->GetNode(nodeId);
    if (node) {
        node->SetPosition(x, y);
        m_Dirty = true;
    }
}

void WorkflowCanvas::MoveSelection(float32 dx, float32 dy) {
    for (const String& nodeId : m_SelectedNodes) {
        if (!m_Graph) continue;
        WorkflowNode* node = m_Graph->GetNode(nodeId);
        if (node) {
            node->SetPosition(node->GetPosX() + dx, node->GetPosY() + dy);
        }
    }
    m_Dirty = true;
}

void WorkflowCanvas::ZoomIn() {
    SetZoom(m_Zoom * 1.2f);
}

void WorkflowCanvas::ZoomOut() {
    SetZoom(m_Zoom / 1.2f);
}

void WorkflowCanvas::FitToView() {
    m_Zoom = 1.0f;
    m_PanX = 0.0f;
    m_PanY = 0.0f;
}

void WorkflowCanvas::Copy() {
}

void WorkflowCanvas::Paste() {
}

void WorkflowCanvas::Duplicate() {
}

void WorkflowCanvas::Delete() {
    for (const String& nodeId : m_SelectedNodes) {
        RemoveNode(nodeId);
    }
    m_Dirty = true;
}

void WorkflowCanvas::Undo() {
}

void WorkflowCanvas::Redo() {
}

void WorkflowCanvas::Render() {
    m_Dirty = false;
}

NodePalette::NodePalette() {
}

void NodePalette::SetCategories(const Vector<String>& categories) {
    m_Categories = categories;
}

Vector<String> NodePalette::GetCategories() const {
    return m_Categories;
}

void NodePalette::AddNodeTemplate(const String& category, const String& name, const String& nodeType) {
    m_NodeTemplates[category].PushBack(name);
}

Vector<String> NodePalette::GetNodeNames(const String& category) const {
    auto it = m_NodeTemplates.Find(category);
    if (it != m_NodeTemplates.End()) {
        return it->second;
    }
    return Vector<String>();
}

void NodePalette::Search(const String& query, Vector< Pair<String, String> >& results) {
}

PropertiesPanel::PropertiesPanel()
    : m_Node(nullptr)
{
}

void PropertiesPanel::SetNode(WorkflowNode* node) {
    m_Node = node;
    Refresh();
}

WorkflowNode* PropertiesPanel::GetNode() const {
    return m_Node;
}

void PropertiesPanel::Refresh() {
}

void PropertiesPanel::SetOnPropertyChanged(std::function<void(const String&, const Variant&)> callback) {
    m_OnPropertyChanged = callback;
}

WorkflowToolbar::WorkflowToolbar()
    : m_Executing(false)
    , m_Progress(0.0f)
{
}

void WorkflowToolbar::Execute() {
    m_Executing = true;
}

void WorkflowToolbar::Abort() {
    m_Executing = false;
}

bool WorkflowToolbar::IsExecuting() const {
    return m_Executing;
}

float32 WorkflowToolbar::GetProgress() const {
    return m_Progress;
}

void WorkflowToolbar::QueuePrompt() {
}

void WorkflowToolbar::ClearQueue() {
}

AICapabilitiesPanel::AICapabilitiesPanel() {
}

void AICapabilitiesPanel::AddGenerationCapability(GenerationType type, const String& name, const String& description) {
    m_Capabilities.PushBack(type);
}

Vector<AICapabilitiesPanel::GenerationType> AICapabilitiesPanel::GetAvailableCapabilities() const {
    return m_Capabilities;
}

void AICapabilitiesPanel::OnCapabilitySelected(GenerationType type) {
}

void AICapabilitiesPanel::SetOnGenerationRequested(std::function<void(GenerationType, const Map<String, Variant>&)> callback) {
    m_OnGenerationRequested = callback;
}

ModelManager::ModelManager()
    : m_MemoryUsage(0)
{
}

void ModelManager::ScanModels(const String& directory) {
}

Vector<String> ModelManager::GetAvailableModels() const {
    return Vector<String>();
}

Vector<String> ModelManager::GetModelsByType(const String& type) const {
    return Vector<String>();
}

bool ModelManager::LoadModel(const String& path) {
    m_LoadedModels.PushBack(path);
    return true;
}

void ModelManager::UnloadModel(const String& path) {
    for (auto it = m_LoadedModels.Begin(); it != m_LoadedModels.End(); ++it) {
        if (*it == path) {
            m_LoadedModels.Erase(it);
            break;
        }
    }
}

float32 ModelManager::GetModelMemoryUsage() const {
    return (float32)m_MemoryUsage / (1024.0f * 1024.0f * 1024.0f);
}

QueuePanel::QueuePanel()
    : m_Processing(false)
{
}

void QueuePanel::AddToQueue(const String& workflowName, int32 priority) {
    QueueItem item;
    item.workflowName = workflowName;
    item.priority = priority;
    item.position = (int32)m_Queue.Size();
    m_Queue.PushBack(item);
}

void QueuePanel::RemoveFromQueue(int32 index) {
    if (index >= 0 && index < m_Queue.Size()) {
        m_Queue.Erase(m_Queue.Begin() + index);
    }
}

void QueuePanel::ClearQueue() {
    m_Queue.Clear();
}

int32 QueuePanel::GetQueueSize() const {
    return (int32)m_Queue.Size();
}

bool QueuePanel::IsProcessing() const {
    return m_Processing;
}

void QueuePanel::StartProcessing() {
    m_Processing = true;
}

void QueuePanel::StopProcessing() {
    m_Processing = false;
}

}
