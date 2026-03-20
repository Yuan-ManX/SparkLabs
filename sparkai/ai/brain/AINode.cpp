#include "AINode.h"
#include "AIBrain.h"

namespace SparkLabs {

IMPLEMENT_RTTI(AINode)

AINode::AINode()
    : m_Priority(0)
    , m_CurrentState(AIState::Inactive) {
}

AINode::~AINode() {
}

void AINode::OnUpdate(float32 deltaTime) {
    (void)deltaTime;
}

void AINode::OnInitialized() {
}

void AINode::OnDestroyed() {
    Deactivate();
}

void AINode::Activate() {
    if (m_CurrentState != AIState::Active) {
        m_CurrentState = AIState::Active;
    }
}

void AINode::Deactivate() {
    m_CurrentState = AIState::Inactive;
}

void AINode::Pause() {
    if (m_CurrentState == AIState::Active) {
        m_CurrentState = AIState::Paused;
    }
}

void AINode::Resume() {
    if (m_CurrentState == AIState::Paused) {
        m_CurrentState = AIState::Active;
    }
}

}