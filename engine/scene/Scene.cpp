#include "Scene.h"
#include "GameObject.h"

namespace SparkLabs {

Scene::Scene()
{
    m_Name = "Untitled";
    m_Root = new GameObject();
    m_Root->SetName("SceneRoot");
}

Scene::~Scene() {
    m_Entities.Clear();
    m_Root = nullptr;
}

void Scene::SetName(const String& name) {
    m_Name = name;
}

const String& Scene::GetName() const {
    return m_Name;
}

GameObject* Scene::GetRoot() const {
    return m_Root.Get();
}

GameObject* Scene::CreateEntity(const String& name) {
    GameObject* entity = new GameObject();
    entity->SetName(name);
    AddEntity(entity);
    return entity;
}

void Scene::AddEntity(GameObject* entity) {
    if (!entity) return;
    m_Root->AddChild(entity);
    m_Entities.PushBack(SmartPtr<GameObject>(entity));
}

void Scene::RemoveEntity(GameObject* entity) {
    if (!entity) return;
    entity->RemoveFromParent();
    for (size_t i = 0; i < m_Entities.Size(); ++i) {
        if (m_Entities[i].Get() == entity) {
            m_Entities.Erase(i);
            return;
        }
    }
}

GameObject* Scene::FindEntity(StringHash id) {
    for (auto& entity : m_Entities) {
        if (entity->GetType().GetHash() == id) {
            return entity.Get();
        }
    }
    return nullptr;
}

GameObject* Scene::FindEntityByName(const String& name) {
    for (auto& entity : m_Entities) {
        if (entity->GetName() == name) {
            return entity.Get();
        }
    }
    return nullptr;
}

Vector<GameObject*> Scene::GetEntitiesWithTag(const String& tag) {
    Vector<GameObject*> results;
    for (auto& entity : m_Entities) {
        if (entity->GetTag() == tag) {
            results.PushBack(entity.Get());
        }
    }
    return results;
}

void Scene::Update(float32 deltaTime) {
    OnUpdate(deltaTime);
    for (auto& entity : m_Entities) {
        if (entity->IsActive()) {
            entity->OnUpdate(deltaTime);
        }
    }
}

void Scene::FixedUpdate(float32 deltaTime) {
    for (auto& entity : m_Entities) {
        if (entity->IsActive()) {
            for (int i = 0; i < entity->GetChildCount(); ++i) {
                if (GameObject* child = DynamicCast<GameObject*>(entity->GetChild(i))) {
                    child->OnFixedUpdate(deltaTime);
                }
            }
        }
    }
}

void Scene::LateUpdate(float32 deltaTime) {
    for (auto& entity : m_Entities) {
        if (entity->IsActive()) {
            for (int i = 0; i < entity->GetChildCount(); ++i) {
                if (GameObject* child = DynamicCast<GameObject*>(entity->GetChild(i))) {
                    child->OnLateUpdate(deltaTime);
                }
            }
        }
    }
}

void Scene::OnUpdate(float32 deltaTime) {
}

}
