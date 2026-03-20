#include "DifficultyController.h"

namespace SparkLabs {

DifficultyController::DifficultyController()
    : m_CurrentDifficulty(0.5f)
    , m_TargetDifficulty(0.5f)
    , m_MinDifficulty(0.0f)
    , m_MaxDifficulty(1.0f)
    , m_AdjustmentRate(0.1f)
{
}

void DifficultyController::Update(const PlayerModel& player) {
    float32 skill = player.GetOverallSkill();
    float32 diff = m_TargetDifficulty - m_CurrentDifficulty;
    m_CurrentDifficulty += diff * m_AdjustmentRate;
}

void DifficultyController::SetTargetDifficulty(float32 difficulty) {
    m_TargetDifficulty = Math::Clamp(difficulty, m_MinDifficulty, m_MaxDifficulty);
}

float32 DifficultyController::GetCurrentDifficulty() const {
    return m_CurrentDifficulty;
}

Map<StringHash, float32> DifficultyController::GetDifficultyParameters() {
    return m_DifficultyParams;
}

void DifficultyController::SetDifficultyRange(float32 min, float32 max) {
    m_MinDifficulty = min;
    m_MaxDifficulty = max;
}

}
