#ifndef SPARKLABS_ENGINE_GAMEPLAY_PLAYERMODEL_H
#define SPARKLABS_ENGINE_GAMEPLAY_PLAYERMODEL_H

#include <Object.h>
#include <Vector.h>
#include <StringHash.h>

namespace SparkLabs {

struct GameEvent {
    StringHash type;
    float32 deltaTime;
    bool success;
    Vector3 position;
    float64 timestamp;
};

class PlayerModel : public Object {
    SPARKLABS_OBJECT(PlayerModel)
public:
    PlayerModel();

    void RecordEvent(const GameEvent& event);
    void UpdateSkills(float32 deltaTime);

    float32 GetSkillLevel(const StringHash skill) const;
    Vector<StringHash> GetWeakSkills(int32 count = 3);
    Vector<StringHash> GetStrongSkills(int32 count = 3);

    float32 GetOverallSkill() const;
    float32 GetExperience() const;
    int32 GetLevel() const;

private:
    Map<StringHash, float32> m_SkillLevels;
    float32 m_OverallSkill;
    float32 m_Experience;
    int32 m_Level;
    Vector<GameEvent> m_RecentEvents;
};

}

#endif
