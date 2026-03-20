#include "AIBrain.h"
#include <algorithm>

namespace SparkLabs {

IMPLEMENT_RTTI(AIBrain)

AIBrain::AIBrain()
    : m_RootNode(nullptr) {
    m_Blackboard = MakeSmartPtr<AIBlackboard>();
    m_EventBus = MakeSmartPtr<AIEventBus>();
}

AIBrain::~AIBrain() {
    for (size_t i = 0; i < m_AttachedNodes.Size(); ++i) {
        if (m_AttachedNodes[i]) {
            m_AttachedNodes[i]->OnDestroyed();
        }
    }
    m_AttachedNodes.Clear();
}

void AIBrain::OnUpdate(float32 deltaTime) {
    if (!IsEnabled()) return;

    UpdateNodes(deltaTime);
    ProcessExpiredMemory();

    if (m_EventBus) {
        m_EventBus->Update(0.0);
    }
}

void AIBrain::AttachNode(AINode* node) {
    if (!node) return;

    for (size_t i = 0; i < m_AttachedNodes.Size(); ++i) {
        if (m_AttachedNodes[i] == node) return;
    }

    m_AttachedNodes.PushBack(node);
    node->OnInitialized();

    std::sort(m_AttachedNodes.Begin(), m_AttachedNodes.End(),
        [](AINode* a, AINode* b) {
            return a->GetPriority() < b->GetPriority();
        });
}

void AIBrain::DetachNode(AINode* node) {
    if (!node) return;

    for (size_t i = 0; i < m_AttachedNodes.Size(); ++i) {
        if (m_AttachedNodes[i] == node) {
            node->OnDestroyed();
            m_AttachedNodes.Erase(i);
            return;
        }
    }
}

void AIBrain::SetNeuralNetwork(SmartPtr<NeuralNetwork> network) {
    m_NeuralNetwork = network;
}

TensorRef AIBrain::Think(const TensorRef& input) {
    if (!m_NeuralNetwork || !input.IsValid()) {
        return TensorRef();
    }
    return m_NeuralNetwork->Forward(input);
}

void AIBrain::AddMemory(const AIMemoryEntry& entry) {
    m_Memory.PushBack(entry);
}

void AIBrain::ClearMemory() {
    m_Memory.Clear();
}

void AIBrain::AddToMemory(const String& content, MemoryType type, float64 importance) {
    AIMemoryEntry entry;
    entry.content = content;
    entry.type = type;
    entry.importance = importance;
    entry.timestamp = 0.0;
    entry.expiresAt = 0.0;
    m_Memory.PushBack(entry);
}

void AIBrain::UpdateNodes(float32 deltaTime) {
    for (size_t i = 0; i < m_AttachedNodes.Size(); ++i) {
        AINode* node = m_AttachedNodes[i];
        if (node && node->IsEnabled() && node->IsActive()) {
            node->OnUpdate(deltaTime);
        }
    }
}

void AIBrain::ProcessExpiredMemory() {
    for (size_t i = m_Memory.Size(); i > 0; --i) {
        if (m_Memory[i - 1].IsExpired()) {
            m_Memory.Erase(i - 1);
        }
    }
}

}