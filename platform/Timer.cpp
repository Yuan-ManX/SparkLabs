#include "Timer.h"
#include <chrono>

namespace SparkLabs {

int64 Timer::s_StartupTime = 0;
int64 Timer::s_FrameCount = 0;

Timer::Timer() : m_Started(false), m_Paused(false), m_StartTime(0), m_PausedTime(0), m_LastTickTime(0) {
}

void Timer::Initialize() {
    s_StartupTime = GetCurrentTimeMicroseconds();
    s_FrameCount = 0;
}

void Timer::Shutdown() {
}

int64 Timer::GetCurrentTimeMicroseconds() {
    auto now = std::chrono::high_resolution_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::microseconds>(duration).count();
}

void Timer::Start() {
    m_Started = true;
    m_Paused = false;
    m_StartTime = GetCurrentTimeMicroseconds();
    m_PausedTime = 0;
    m_LastTickTime = m_StartTime;
}

void Timer::Stop() {
    m_Started = false;
    m_Paused = false;
}

void Timer::Pause() {
    if (m_Started && !m_Paused) {
        m_PausedTime = GetCurrentTimeMicroseconds();
        m_Paused = true;
    }
}

void Timer::Resume() {
    if (m_Started && m_Paused) {
        int64 pauseDuration = GetCurrentTimeMicroseconds() - m_PausedTime;
        m_StartTime += pauseDuration;
        m_Paused = false;
    }
}

float64 Timer::GetElapsedSeconds() {
    return static_cast<float64>(GetElapsedMicroseconds()) / 1000000.0;
}

int64 Timer::GetElapsedMilliseconds() {
    return GetElapsedMicroseconds() / 1000;
}

int64 Timer::GetElapsedMicroseconds() {
    if (!m_Started) {
        return 0;
    }
    int64 currentTime = GetCurrentTimeMicroseconds();
    if (m_Paused) {
        return m_PausedTime - m_StartTime;
    }
    return currentTime - m_StartTime;
}

float64 Timer::GetTimeSinceStartup() {
    int64 currentTime = GetCurrentTimeMicroseconds();
    return static_cast<float64>(currentTime - s_StartupTime) / 1000000.0;
}

int64 Timer::GetFrameCount() {
    return s_FrameCount;
}

void Timer::IncrementFrameCount() {
    ++s_FrameCount;
}

}
