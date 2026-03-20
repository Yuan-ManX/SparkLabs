#ifndef SPARKAI_AI_BRAIN_AIBRAIN_H
#define SPARKAI_AI_BRAIN_AIBRAIN_H

#include "../../engine/scene/Component.h"
#include "../../core/memory/SmartPtr.h"
#include "AINode.h"
#include "AIBlackboard.h"
#include "AIEventBus.h"
#include "NeuralNetwork.h"
#include "AIMemoryEntry.h"
#include "TensorRef.h"

namespace SparkLabs {

class AIBrain : public Component {
    DECLARE_RTTI

public:
    AIBrain();
    virtual ~AIBrain();

    virtual void OnUpdate(float32 deltaTime) override;

    void AttachNode(AINode* node);
    void DetachNode(AINode* node);

    SmartPtr<AINode> GetRootNode() const { return m_RootNode; }
    void SetRootNode(SmartPtr<AINode> root) { m_RootNode = root; }

    SmartPtr<AIBlackboard> GetBlackboard() const { return m_Blackboard; }
    SmartPtr<AIEventBus> GetEventBus() const { return m_EventBus; }
    SmartPtr<NeuralNetwork> GetNeuralNetwork() const { return m_NeuralNetwork; }

    void SetNeuralNetwork(SmartPtr<NeuralNetwork> network);

    TensorRef Think(const TensorRef& input);

    const Vector<AIMemoryEntry>& GetMemory() const { return m_Memory; }
    void AddMemory(const AIMemoryEntry& entry);
    void ClearMemory();

    void AddToMemory(const String& content, MemoryType type, float64 importance = 0.5);

private:
    void UpdateNodes(float32 deltaTime);
    void ProcessExpiredMemory();

    SmartPtr<AINode> m_RootNode;
    SmartPtr<AIBlackboard> m_Blackboard;
    SmartPtr<AIEventBus> m_EventBus;
    SmartPtr<NeuralNetwork> m_NeuralNetwork;
    Vector<AIMemoryEntry> m_Memory;
    Vector<AINode*> m_AttachedNodes;
};

}

#endif