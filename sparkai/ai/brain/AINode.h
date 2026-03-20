#ifndef SPARKAI_AI_BRAIN_AINODE_H
#define SPARKAI_AI_BRAIN_AINODE_H

#include "../../engine/scene/Component.h"
#include "../../core/Types.h"

namespace SparkLabs {

enum class AIState {
    Inactive,
    Active,
    Paused
};

class AINode : public Component {
    DECLARE_RTTI

public:
    AINode();
    virtual ~AINode();

    virtual void OnUpdate(float32 deltaTime) override;
    virtual void OnInitialized();
    virtual void OnDestroyed() override;

    int32 GetPriority() const { return m_Priority; }
    void SetPriority(int32 priority) { m_Priority = priority; }

    AIState GetCurrentState() const { return m_CurrentState; }
    void SetCurrentState(AIState state) { m_CurrentState = state; }

    void Activate();
    void Deactivate();
    void Pause();
    void Resume();

    bool IsActive() const { return m_CurrentState == AIState::Active; }
    bool IsInactive() const { return m_CurrentState == AIState::Inactive; }
    bool IsPaused() const { return m_CurrentState == AIState::Paused; }

protected:
    int32 m_Priority;
    AIState m_CurrentState;
};

}

#endif