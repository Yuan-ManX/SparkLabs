#pragma once

#include "../core/Types.h"
#include "../core/string/String.h"
#include "../core/memory/SmartPtr.h"
#include "../engine/scene/GameObject.h"

namespace SparkLabs {

class AIEditorPanel;

class SceneEditor {
public:
    SceneEditor();
    ~SceneEditor();

    void OpenScene(const String& path);
    void SaveScene(const String& path);
    void NewScene();

    void SelectObject(GameObject* obj);
    GameObject* GetSelectedObject() const { return m_SelectedObject; }

    void SetGridVisible(bool visible) { m_GridVisible = visible; }
    bool IsGridVisible() const { return m_GridVisible; }

    void SetGizmoMode(GizmoMode mode) { m_GizmoMode = mode; }
    GizmoMode GetGizmoMode() const { return m_GizmoMode; }

    enum class GizmoMode { Translate, Rotate, Scale };

    void Update(float32 deltaTime);
    void Render();

    SmartPtr<AIEditorPanel> GetAIEditorPanel() const { return m_AIEditorPanel; }

private:
    SmartPtr<GameObject> m_CurrentScene;
    GameObject* m_SelectedObject;
    bool m_GridVisible;
    GizmoMode m_GizmoMode;
    SmartPtr<AIEditorPanel> m_AIEditorPanel;
};

}
