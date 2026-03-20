#include "Agent.h"
#include "BehaviorTree.h"
#include "../../engine/scene/GameObject.h"
#include "../../engine/scene/Transform.h"

namespace SparkLabs {

Agent::Agent()
{
}

Agent::~Agent() {
    m_BehaviorTree.Reset();
    m_Blackboard.Reset();
}

Vector3 Agent::GetPosition() const {
    auto gameObject = m_GameObject.Lock();
    if (gameObject) {
        return gameObject->GetWorldPosition();
    }
    return Vector3::Zero();
}

Quaternion Agent::GetRotation() const {
    auto gameObject = m_GameObject.Lock();
    if (gameObject) {
        return gameObject->GetWorldRotation();
    }
    return Quaternion::Identity();
}

void Agent::SendEvent(const AIEvent& event) {
    if (m_Blackboard) {
        StringHash eventKey(event.eventType.GetHash() + 1);
        m_Blackboard->SetValue(eventKey, Variant());
    }
}

Variant Agent::GetProperty(const StringHash& key) const {
    auto it = m_Properties.find(key.GetHash());
    if (it != m_Properties.end()) {
        return it->second;
    }
    return Variant();
}

void Agent::SetProperty(const StringHash& key, const Variant& value) {
    m_Properties[key.GetHash()] = value;
}

bool Agent::HasProperty(const StringHash& key) const {
    return m_Properties.find(key.GetHash()) != m_Properties.end();
}

AIBlackboard::AIBlackboard()
{
}

AIBlackboard::~AIBlackboard() {
    Clear();
}

Variant AIBlackboard::GetValue(const StringHash& key) const {
    auto it = m_Values.find(key.GetHash());
    if (it != m_Values.end()) {
        return it->second;
    }
    return Variant();
}

void AIBlackboard::SetValue(const StringHash& key, const Variant& value) {
    m_Values[key.GetHash()] = value;
}

bool AIBlackboard::HasValue(const StringHash& key) const {
    return m_Values.find(key.GetHash()) != m_Values.end();
}

void AIBlackboard::RemoveValue(const StringHash& key) {
    m_Values.erase(key.GetHash());
}

void AIBlackboard::Clear() {
    m_Values.clear();
}

}
