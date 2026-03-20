#ifndef SPARKLABS_ENGINE_GAMEPLAY_DIFFICULTYCONTROLLER_H
#define SPARKLABS_ENGINE_GAMEPLAY_DIFFICULTYCONTROLLER_H

#include <Object.h>
#include <StringHash.h>

namespace SparkLabs {

class PlayerModel;

class DifficultyController : public Object {
    SPARKLABS_OBJECT(DifficultyController)
public:
    DifficultyController();

    void Update(const PlayerModel& player);

    void SetTargetDifficulty(float32 difficulty);
    float32 GetCurrentDifficulty() const;

    Map<StringHash, float32> GetDifficultyParameters();

    void SetDifficultyRange(float32 min, float32 max);

private:
    float32 m_CurrentDifficulty;
    float32 m_TargetDifficulty;
    float32 m_MinDifficulty;
    float32 m_MaxDifficulty;
    float32 m_AdjustmentRate;
    Map<StringHash, float32> m_DifficultyParams;
};

}

#endif
