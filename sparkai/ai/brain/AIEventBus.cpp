#include "AIEventBus.h"
#include <algorithm>

namespace SparkLabs {

AIEventBus::AIEventBus() {
}

AIEventBus::~AIEventBus() {
    Clear();
}

void AIEventBus::Subscribe(StringHash eventType, EventCallback callback, int32 priority) {
    AIEventSubscription subscription;
    subscription.callback = std::move(callback);
    subscription.priority = priority;

    auto it = m_Subscribers.find(eventType);
    if (it == m_Subscribers.end()) {
        SubscriptionList list;
        list.PushBack(std::move(subscription));
        m_Subscribers[eventType] = std::move(list);
    } else {
        it->second.PushBack(std::move(subscription));
        std::sort(it->second.Begin(), it->second.End());
    }
}

void AIEventBus::Unsubscribe(StringHash eventType, EventCallback callback) {
    auto it = m_Subscribers.find(eventType);
    if (it != m_Subscribers.end()) {
        auto& list = it->second;
        for (size_t i = 0; i < list.Size(); ++i) {
            if (list[i].callback.target_type() == callback.target_type()) {
                list.Erase(i);
                break;
            }
        }
        if (list.Empty()) {
            m_Subscribers.erase(it);
        }
    }
}

void AIEventBus::Publish(const AIEvent& event) {
    m_EventQueue.push(event);
}

void AIEventBus::Update(float64 currentTime) {
    while (!m_EventQueue.empty()) {
        AIEvent event = m_EventQueue.top();
        m_EventQueue.pop();

        if (event.timestamp <= currentTime) {
            auto it = m_Subscribers.find(event.type);
            if (it != m_Subscribers.end()) {
                DeliverEvent(event, it->second);
            }
        } else {
            m_EventQueue.push(event);
            break;
        }
    }
}

void AIEventBus::DeliverEvent(const AIEvent& event, const SubscriptionList& subscribers) {
    for (size_t i = 0; i < subscribers.Size(); ++i) {
        if (subscribers[i].callback) {
            subscribers[i].callback(event);
        }
    }
}

void AIEventBus::Clear() {
    m_Subscribers.clear();
    while (!m_EventQueue.empty()) {
        m_EventQueue.pop();
    }
}

}