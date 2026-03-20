#pragma once

#include "../core/Types.h"

namespace SparkLabs {

class Timer {
public:
    Timer();

    void Start();
    void Stop();
    void Pause();
    void Resume();

    float64 GetElapsedSeconds();
    int64 GetElapsedMilliseconds();
    int64 GetElapsedMicroseconds();

    bool IsRunning() const { return m_Running && !m_Paused; }
    bool IsPaused() const { return m_Paused; }
    bool IsStarted() const { return m_Started; }

    static float64 GetTimeSinceStartup();
    static int64 GetFrameCount();
    static void IncrementFrameCount();
    static void Initialize();
    static void Shutdown();

private:
    int64 GetCurrentTimeMicroseconds();

    bool m_Started;
    bool m_Paused;
    int64 m_StartTime;
    int64 m_PausedTime;
    int64 m_LastTickTime;

    static int64 s_StartupTime;
    static int64 s_FrameCount;
};

}
