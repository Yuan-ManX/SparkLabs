#pragma once

#include <mutex>

namespace SparkLabs {

    class Mutex {
    public:
        void Lock() { m_Mutex.lock(); }
        void Unlock() { m_Mutex.unlock(); }
        bool TryLock() { return m_Mutex.try_lock(); }

    private:
        std::mutex m_Mutex;
    };

    class LockGuard {
    public:
        explicit LockGuard(Mutex& mutex) : m_Mutex(mutex) { m_Mutex.Lock(); }
        ~LockGuard() { m_Mutex.Unlock(); }

    private:
        LockGuard(const LockGuard&) = delete;
        LockGuard& operator=(const LockGuard&) = delete;

        Mutex& m_Mutex;
    };

}