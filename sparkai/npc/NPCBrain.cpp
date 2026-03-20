#include "NPCBrain.h"

namespace SparkLabs {

NPCBrainComponent::NPCBrainComponent()
    : m_Personality(nullptr)
{
}

NPCBrainComponent::~NPCBrainComponent() {
}

void NPCBrainComponent::OnUpdate(float32 deltaTime) {
}

void NPCBrainComponent::LoadDecisionModel(const String& path) {
}

void NPCBrainComponent::LoadDialogueModel(const String& path) {
}

String NPCBrainComponent::GenerateDialogue(const String& context) {
    return "";
}

void NPCBrainComponent::SetPersonality(const NPCPersonality& personality) {
}

const NPCPersonality& NPCBrainComponent::GetPersonality() const {
    static NPCPersonality empty;
    return empty;
}

void NPCBrainComponent::Remember(const String& content, float32 importance) {
}

Vector<String> NPCBrainComponent::Recall(const String& query, int32 maxResults) {
    return Vector<String>();
}

void NPCBrainComponent::AddAttentionTarget(void* agent, float32 priority) {
}

void* NPCBrainComponent::GetMostImportantTarget() {
    return nullptr;
}

void NPCBrainComponent::ModifyEmotion(const String& emotion, float32 delta) {
}

String NPCBrainComponent::GetDominantEmotion() {
    return "";
}

}
