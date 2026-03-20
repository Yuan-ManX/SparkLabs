#pragma once

#include <vector>
#include <functional>

namespace SparkLabs {

    template<typename... Args>
    class Signal {
    public:
        using Callback = std::function<void(Args...)>;

        int Connect(Callback callback) {
            int id = m_NextID++;
            m_Callbacks.emplace_back(id, std::move(callback));
            return id;
        }

        void Disconnect(int id) {
            for (auto it = m_Callbacks.begin(); it != m_Callbacks.end(); ++it) {
                if (it->first == id) {
                    m_Callbacks.erase(it);
                    return;
                }
            }
        }

        void Emit(Args... args) {
            for (auto& pair : m_Callbacks) {
                pair.second(args...);
            }
        }

        void Clear() {
            m_Callbacks.clear();
        }

    private:
        std::vector<std::pair<int, Callback>> m_Callbacks;
        int m_NextID = 0;
    };

}