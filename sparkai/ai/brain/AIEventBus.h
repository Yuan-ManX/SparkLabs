#ifndef SPARKAI_AI_BRAIN_AIEVENTBUS_H
#define SPARKAI_AI_BRAIN_AIEVENTBUS_H

#include "../../core/Types.h"
#include "../../core/string/StringHash.h"
#include "../../core/io/Vector.h"
#include "AIBlackboard.h"
#include <map>
#include <queue>
#include <functional>

namespace SparkLabs {

struct AIEvent {
    StringHash type;
    float64 timestamp;
    Map<StringHash, Variant> data;

    AIEvent()
        : timestamp(0.0) {
    }

    AIEvent(StringHash eventType)
        : type(eventType)
        , timestamp(0.0) {
    }

    AIEvent(StringHash eventType, float64 time)
        : type(eventType)
        , timestamp(time) {
    }

    template<typename T>
    void SetData(const String& key, const T& value) {
        StringHash hash(key);
        data.Set(hash, Variant(value));
    }

    template<typename T>
    T GetData(const String& key, const T& defaultValue = T()) const {
        StringHash hash(key);
        const Variant* value = data.Get(hash);
        if (value) {
            return value->Get<T>();
        }
        return defaultValue;
    }
};

struct AIEventSubscription {
    EventCallback callback;
    int32 priority;

    bool operator<(const AIEventSubscription& other) const {
        return priority < other.priority;
    }
};

class AIEventBus {
public:
    AIEventBus();
    ~AIEventBus();

    using EventCallback = std::function<void(const AIEvent&)>;

    void Subscribe(StringHash eventType, EventCallback callback, int32 priority = 0);
    void Unsubscribe(StringHash eventType, EventCallback callback);
    void Publish(const AIEvent& event);

    void Update(float64 currentTime);

    void Clear();

private:
    using SubscriptionList = Vector<AIEventSubscription>;
    std::map<StringHash, SubscriptionList> m_Subscribers;

    std::priority_queue<AIEvent> m_EventQueue;

    void DeliverEvent(const AIEvent& event, const SubscriptionList& subscribers);
};

}

#endif