#ifndef SPARKLABS_SPARKAI_UI_WORKFLOWCANVAS_H
#define SPARKLABS_SPARKAI_UI_WORKFLOWCANVAS_H

#include "../workflow/WorkflowGraph.h"
#include <Vector.h>
#include <String.h>

namespace SparkLabs {

class WorkflowCanvas {
public:
    WorkflowCanvas();
    ~WorkflowCanvas();

    void SetGraph(WorkflowGraph* graph);
    WorkflowGraph* GetGraph() const;

    void SetZoom(float32 zoom);
    float32 GetZoom() const;

    void SetPan(float32 x, float32 y);
    float32 GetPanX() const;
    float32 GetPanY() const;

    void AddNode(WorkflowNode* node, float32 x, float32 y);
    void RemoveNode(const String& nodeId);

    void Connect(const String& sourceNodeId, int32 sourcePin, const String& targetNodeId, int32 targetPin);
    void Disconnect(const String& edgeId);

    void SelectNode(const String& nodeId);
    void SelectNodes(const Vector<String>& nodeIds);
    void ClearSelection();
    Vector<String> GetSelectedNodes() const;

    void MoveNode(const String& nodeId, float32 x, float32 y);
    void MoveSelection(float32 dx, float32 dy);

    void ZoomIn();
    void ZoomOut();
    void FitToView();

    void Copy();
    void Paste();
    void Duplicate();
    void Delete();

    void Undo();
    void Redo();

    void Render();

private:
    WorkflowGraph* m_Graph;
    float32 m_Zoom;
    float32 m_PanX;
    float32 m_PanY;
    Vector<String> m_SelectedNodes;
    bool m_Dirty;
};

class NodePalette {
public:
    NodePalette();

    void SetCategories(const Vector<String>& categories);
    Vector<String> GetCategories() const;

    void AddNodeTemplate(const String& category, const String& name, const String& nodeType);
    Vector<String> GetNodeNames(const String& category) const;

    void Search(const String& query, Vector< Pair<String, String> >& results);

private:
    Vector<String> m_Categories;
    Map<String, Vector<String>> m_NodeTemplates;
};

class PropertiesPanel {
public:
    PropertiesPanel();

    void SetNode(WorkflowNode* node);
    WorkflowNode* GetNode() const;

    void Refresh();

    void SetOnPropertyChanged(std::function<void(const String&, const Variant&)> callback);

private:
    WorkflowNode* m_Node;
    std::function<void(const String&, const Variant&)> m_OnPropertyChanged;
};

class WorkflowToolbar {
public:
    WorkflowToolbar();

    void Execute();
    void Abort();

    bool IsExecuting() const;
    float32 GetProgress() const;

    void QueuePrompt();
    void ClearQueue();

private:
    bool m_Executing;
    float32 m_Progress;
};

class AICapabilitiesPanel {
public:
    AICapabilitiesPanel();

    enum class GenerationType {
        Image,
        Text,
        Video,
        Audio,
        Model,
        Scene,
        Character,
        Animation
    };

    void AddGenerationCapability(GenerationType type, const String& name, const String& description);
    Vector<GenerationType> GetAvailableCapabilities() const;

    void OnCapabilitySelected(GenerationType type);

    void SetOnGenerationRequested(std::function<void(GenerationType, const Map<String, Variant>&)> callback);

private:
    Vector<GenerationType> m_Capabilities;
    std::function<void(GenerationType, const Map<String, Variant>&)> m_OnGenerationRequested;
};

class ModelManager {
public:
    ModelManager();

    void ScanModels(const String& directory);
    Vector<String> GetAvailableModels() const;
    Vector<String> GetModelsByType(const String& type) const;

    bool LoadModel(const String& path);
    void UnloadModel(const String& path);

    float32 GetModelMemoryUsage() const;

    enum class ModelType {
        Checkpoint,
        VAE,
        LoRA,
        Embedding,
        ControlNet,
        Upscale
    };

private:
    Vector<String> m_LoadedModels;
    size_t m_MemoryUsage;
};

class QueuePanel {
public:
    QueuePanel();

    void AddToQueue(const String& workflowName, int32 priority = 0);
    void RemoveFromQueue(int32 index);
    void ClearQueue();

    int32 GetQueueSize() const;
    bool IsProcessing() const;

    void StartProcessing();
    void StopProcessing();

private:
    struct QueueItem {
        String workflowName;
        int32 priority;
        int32 position;
    };

    Vector<QueueItem> m_Queue;
    bool m_Processing;
};

}
