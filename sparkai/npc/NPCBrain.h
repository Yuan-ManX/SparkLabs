#ifndef SPARKLABS_ENGINE_NPC_NPCBRAIN_H
#define SPARKLABS_ENGINE_NPC_NPCBRAIN_H

#include <Object.h>
#include <SmartPtr.h>
#include <Vector3.h>
#include <String.h>

namespace SparkLabs {

class NeuralNetwork;
class AIMemory;
class AttentionMechanism;
class EmotionalState;
class DialogueGenerator;
class NPCPersonality;

class NPCBrainComponent : public Component {
    SPARKLABS_OBJECT(NPCBrainComponent)
public:
    NPCBrainComponent();
    virtual ~NPCBrainComponent();

    virtual void OnUpdate(float32 deltaTime) override;

    void LoadDecisionModel(const String& path);
    void LoadDialogueModel(const String& path);

    String GenerateDialogue(const String& context);

    void SetPersonality(const NPCPersonality& personality);
    const NPCPersonality& GetPersonality() const;

    void Remember(const String& content, float32 importance);
    Vector<String> Recall(const String& query, int32 maxResults = 5);

    void AddAttentionTarget(void* agent, float32 priority);
    void* GetMostImportantTarget();

    void ModifyEmotion(const String& emotion, float32 delta);
    String GetDominantEmotion();

private:
    SmartPtr<NeuralNetwork> m_DecisionNetwork;
    SmartPtr<NeuralNetwork> m_DialogueNetwork;
    SmartPtr<AIMemory> m_Memory;
    SmartPtr<AttentionMechanism> m_Attention;
    SmartPtr<EmotionalState> m_Emotion;
    SmartPtr<DialogueGenerator> m_DialogueGenerator;
    NPCPersonality* m_Personality;
};

}

#endif
