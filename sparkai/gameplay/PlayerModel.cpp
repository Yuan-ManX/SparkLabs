#include "PlayerModel.h"

namespace SparkLabs {

PlayerModel::PlayerModel()
    : m_OverallSkill(0.0f)
    , m_Experience(0.0f)
    , m_Level(1)
{
}

void PlayerModel::RecordEvent(const GameEvent& event) {
    m_RecentEvents.PushBack(event);
    if (m_RecentEvents.Size() > 100) {
        m_RecentEvents.Erase(m_RecentEvents.Begin());
    }
}

void PlayerModel::UpdateSkills(float32 deltaTime) {
}

float32 PlayerModel::GetSkillLevel(const StringHash skill) const {
    auto it = m_SkillLevels.Find(skill);
    if (it != m_SkillLevels.End()) {
        return it->second;
    }
    return 0.0f;
}

Vector<StringHash> PlayerModel::GetWeakSkills(int32 count) {
    return Vector<StringHash>();
}

Vector<StringHash> PlayerModel::GetStrongSkills(int32 count) {
    return Vector<StringHash>();
}

float32 PlayerModel::GetOverallSkill() const {
    return m_OverallSkill;
}

float32 PlayerModel::GetExperience() const {
    return m_Experience;
}

int32 PlayerModel::GetLevel() const {
    return m_Level;
}

}
