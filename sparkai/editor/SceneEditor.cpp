#include "SceneEditor.h"
#include "AIEditorPanel.h"
#include "../platform/FileSystem.h"

namespace SparkLabs {

SceneEditor::SceneEditor()
    : m_SelectedObject(nullptr)
    , m_GridVisible(true)
    , m_GizmoMode(GizmoMode::Translate) {
    m_CurrentScene = MakeSmartPtr<GameObject>("New Scene");
    m_AIEditorPanel = MakeSmartPtr<AIEditorPanel>();
}

SceneEditor::~SceneEditor() {
}

void SceneEditor::OpenScene(const String& path) {
    FileSystem* fs = FileSystem::GetInstance();
    if (!fs) {
        return;
    }

    if (fs->Exists(path)) {
        String content = fs->ReadAllText(path);
        if (!content.Empty()) {
            NewScene();
        }
    }
}

void SceneEditor::SaveScene(const String& path) {
    FileSystem* fs = FileSystem::GetInstance();
    if (!fs) {
        return;
    }

    if (m_CurrentScene) {
        String sceneData = "SceneData";
        fs->WriteAllText(path, sceneData);
    }
}

void SceneEditor::NewScene() {
    m_CurrentScene = MakeSmartPtr<GameObject>("New Scene");
    m_SelectedObject = nullptr;
}

void SceneEditor::SelectObject(GameObject* obj) {
    m_SelectedObject = obj;
}

void SceneEditor::Update(float32 deltaTime) {
    if (m_CurrentScene) {
        m_CurrentScene->Update(deltaTime);
    }
}

void SceneEditor::Render() {
}

}
