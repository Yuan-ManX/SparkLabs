#pragma once

#include "BehaviorTreeNode.h"
#include "../../../core/math/Vector3.h"
#include <functional>
#include <map>

namespace SparkLabs {

class AIBlackboard;
class GameObject;
struct AIEvent;

class Agent {
public:
    Agent();
    ~Agent();

    WeakPtr<GameObject> GetGameObject() const { return m_GameObject; }
    void SetGameObject(WeakPtr<GameObject> gameObject) { m_GameObject = gameObject; }

    SmartPtr<BehaviorTree> GetBehaviorTree() const { return m_BehaviorTree; }
    void SetBehaviorTree(SmartPtr<BehaviorTree> tree) { m_BehaviorTree = tree; }

    SmartPtr<AIBlackboard> GetBlackboard() const { return m_Blackboard; }
    void SetBlackboard(SmartPtr<AIBlackboard> blackboard) { m_Blackboard = blackboard; }

    Vector3 GetPosition() const;
    Quaternion GetRotation() const;

    void SendEvent(const AIEvent& event);

    Variant GetProperty(const StringHash& key) const;
    void SetProperty(const StringHash& key, const Variant& value);
    bool HasProperty(const StringHash& key) const;

private:
    WeakPtr<GameObject> m_GameObject;
    SmartPtr<BehaviorTree> m_BehaviorTree;
    SmartPtr<AIBlackboard> m_Blackboard;
    std::map<uint32_t, Variant> m_Properties;
};

struct AIEvent {
    StringHash eventType;
    std::map<StringHash, Variant> data;
};

class AIBlackboard {
public:
    AIBlackboard();
    ~AIBlackboard();

    Variant GetValue(const StringHash& key) const;
    void SetValue(const StringHash& key, const Variant& value);
    bool HasValue(const StringHash& key) const;
    void RemoveValue(const StringHash& key);
    void Clear();

private:
    std::map<uint32_t, Variant> m_Values;
};

struct Variant {
    enum class Type { None, Int, Float, Bool, String, Vector3, Quaternion };

    Type type;
    int32 intValue;
    float32 floatValue;
    bool boolValue;
    String stringValue;
    Vector3 vector3Value;
    Quaternion quaternionValue;

    Variant() : type(Type::None), intValue(0), floatValue(0.0f), boolValue(false) {}
};

}
