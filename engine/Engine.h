#ifndef SPARKLABS_ENGINE_ENGINE_H
#define SPARKLABS_ENGINE_ENGINE_H

#include "../core/Types.h"
#include "../core/memory/SmartPtr.h"
#include "../core/string/String.h"
#include "scene/Scene.h"

namespace SparkLabs {

class Engine {
public:
    static Engine* GetInstance();

    void Initialize();
    void Shutdown();

    void Run();
    void Stop();

    void SetScene(Scene* scene);
    Scene* GetScene() const;

    bool IsRunning() const { return m_Running; }

    float32 GetDeltaTime() const { return m_DeltaTime; }
    float64 GetTotalTime() const { return m_TotalTime; }

private:
    Engine();
    ~Engine();

    void MainLoop();
    void Update(float32 deltaTime);
    void Render();

    static Engine* s_Instance;

    SmartPtr<Scene> m_Scene;
    bool m_Running;
    bool m_Initialized;
    float32 m_DeltaTime;
    float64 m_TotalTime;
};

}

#endif
