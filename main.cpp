#include <iostream>
#include "core/math/Vector3.h"
#include "core/math/Quaternion.h"
#include "core/math/Matrix4x4.h"
#include "core/memory/SmartPtr.h"
#include "core/string/String.h"
#include "engine/Engine.h"
#include "engine/scene/Scene.h"
#include "engine/scene/GameObject.h"

int main(int argc, char** argv) {
    std::cout << "========================================" << std::endl;
    std::cout << "  SparkLabs Engine" << std::endl;
    std::cout << "  AI-Native Game Engine" << std::endl;
    std::cout << "  Version 1.0.0" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;

    SparkLabs::Engine* engine = SparkLabs::Engine::GetInstance();
    engine->Initialize();

    std::cout << "SparkLabs Engine initialized successfully!" << std::endl;
    std::cout << std::endl;

    std::cout << "System Information:" << std::endl;
    std::cout << "  - Math Library: Vector3, Quaternion, Matrix4x4" << std::endl;
    std::cout << "  - Memory Management: SmartPtr, WeakPtr" << std::endl;
    std::cout << "  - Object System: RTTI enabled" << std::endl;
    std::cout << "  - AI Runtime: Ready" << std::endl;
    std::cout << "  - Neural Rendering: Ready" << std::endl;
    std::cout << std::endl;

    SparkLabs::Scene* scene = new SparkLabs::Scene();
    scene->SetName("DemoScene");
    engine->SetScene(scene);

    SparkLabs::GameObject* player = scene->CreateEntity("Player");
    player->SetPosition(SparkLabs::Vector3(0.0f, 1.0f, 0.0f));
    player->SetTag("Player");

    std::cout << "Created scene: " << scene->GetName().C_str() << std::endl;
    std::cout << "Created player entity at: " << player->GetPosition().x << ", "
              << player->GetPosition().y << ", " << player->GetPosition().z << std::endl;
    std::cout << std::endl;

    engine->Shutdown();

    return 0;
}
