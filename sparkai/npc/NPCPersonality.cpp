#include "NPCPersonality.h"

namespace SparkLabs {

NPCPersonality::NPCPersonality() {
    m_Traits.Resize(5);
    m_Traits[0].name = "Openness";
    m_Traits[1].name = "Conscientiousness";
    m_Traits[2].name = "Extraversion";
    m_Traits[3].name = "Agreeableness";
    m_Traits[4].name = "Neuroticism";
}

float32 NPCPersonality::GetTrait(TraitType type) const {
    if (type >= 0 && type < 5) {
        return m_Traits[type].value;
    }
    return 0.0f;
}

void NPCPersonality::SetTrait(TraitType type, float32 value) {
    if (type >= 0 && type < 5) {
        m_Traits[type].value = value;
    }
}

void NPCPersonality::ModifyTrait(TraitType type, float32 delta) {
    if (type >= 0 && type < 5) {
        m_Traits[type].value += delta;
    }
}

float32 NPCPersonality::GetOpenness() const { return GetTrait(Openness); }
float32 NPCPersonality::GetConscientiousness() const { return GetTrait(Conscientiousness); }
float32 NPCPersonality::GetExtraversion() const { return GetTrait(Extraversion); }
float32 NPCPersonality::GetAgreeableness() const { return GetTrait(Agreeableness); }
float32 NPCPersonality::GetNeuroticism() const { return GetTrait(Neuroticism); }

}
