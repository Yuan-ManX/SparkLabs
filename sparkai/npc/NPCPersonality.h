#ifndef SPARKLABS_ENGINE_NPC_NPCPERSONALITY_H
#define SPARKLABS_ENGINE_NPC_NPCPERSONALITY_H

#include <String.h>

namespace SparkLabs {

struct PersonalityTrait {
    String name;
    float32 value;
};

class NPCPersonality {
public:
    enum TraitType {
        Openness,
        Conscientiousness,
        Extraversion,
        Agreeableness,
        Neuroticism
    };

    NPCPersonality();

    float32 GetTrait(TraitType type) const;
    void SetTrait(TraitType type, float32 value);
    void ModifyTrait(TraitType type, float32 delta);

    float32 GetOpenness() const;
    float32 GetConscientiousness() const;
    float32 GetExtraversion() const;
    float32 GetAgreeableness() const;
    float32 GetNeuroticism() const;

private:
    Vector<PersonalityTrait> m_Traits;
};

}

#endif
