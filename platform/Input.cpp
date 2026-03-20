#include "Input.h"

namespace SparkLabs {

bool Input::s_KeyStates[256] = { false };
bool Input::s_PrevKeyStates[256] = { false };
bool Input::s_MouseButtonStates[3] = { false };
bool Input::s_PrevMouseButtonStates[3] = { false };
float32 Input::s_MouseX = 0.0f;
float32 Input::s_MouseY = 0.0f;
float32 Input::s_ScrollDelta = 0.0f;
bool Input::s_GamepadConnected[4] = { false, false, false, false };
Vector2 Input::s_GamepadLeftStick[4] = { Vector2::Zero, Vector2::Zero, Vector2::Zero, Vector2::Zero };
Vector2 Input::s_GamepadRightStick[4] = { Vector2::Zero, Vector2::Zero, Vector2::Zero, Vector2::Zero };
float32 Input::s_GamepadTrigger[4][2] = { { 0.0f, 0.0f }, { 0.0f, 0.0f }, { 0.0f, 0.0f }, { 0.0f, 0.0f } };

void Input::Initialize() {
    for (int32 i = 0; i < 256; ++i) {
        s_KeyStates[i] = false;
        s_PrevKeyStates[i] = false;
    }
    for (int32 i = 0; i < 3; ++i) {
        s_MouseButtonStates[i] = false;
        s_PrevMouseButtonStates[i] = false;
    }
    s_MouseX = 0.0f;
    s_MouseY = 0.0f;
    s_ScrollDelta = 0.0f;
}

void Input::Shutdown() {
}

void Input::Update() {
    for (int32 i = 0; i < 256; ++i) {
        s_PrevKeyStates[i] = s_KeyStates[i];
    }
    for (int32 i = 0; i < 3; ++i) {
        s_PrevMouseButtonStates[i] = s_MouseButtonStates[i];
    }
    s_ScrollDelta = 0.0f;
}

bool Input::IsKeyDown(KeyCode key) {
    uint32 index = static_cast<uint32>(key);
    if (index < 256) {
        return s_KeyStates[index];
    }
    return false;
}

bool Input::IsKeyPressed(KeyCode key) {
    uint32 index = static_cast<uint32>(key);
    if (index < 256) {
        return s_KeyStates[index] && !s_PrevKeyStates[index];
    }
    return false;
}

bool Input::IsMouseButtonDown(MouseButton button) {
    uint32 index = static_cast<uint32>(button);
    if (index < 3) {
        return s_MouseButtonStates[index];
    }
    return false;
}

Vector2 Input::GetMousePosition() {
    return Vector2(s_MouseX, s_MouseY);
}

float32 Input::GetMouseX() {
    return s_MouseX;
}

float32 Input::GetMouseY() {
    return s_MouseY;
}

float32 Input::GetMouseScrollDelta() {
    return s_ScrollDelta;
}

bool Input::IsGamepadConnected(int32 index) {
    if (index >= 0 && index < 4) {
        return s_GamepadConnected[index];
    }
    return false;
}

Vector2 Input::GetGamepadLeftStick(int32 index) {
    if (index >= 0 && index < 4) {
        return s_GamepadLeftStick[index];
    }
    return Vector2::Zero;
}

Vector2 Input::GetGamepadRightStick(int32 index) {
    if (index >= 0 && index < 4) {
        return s_GamepadRightStick[index];
    }
    return Vector2::Zero;
}

float32 Input::GetGamepadTrigger(int32 index, bool isLeft) {
    if (index >= 0 && index < 4) {
        return s_GamepadTrigger[index][isLeft ? 0 : 1];
    }
    return 0.0f;
}

void Input::SetMousePosition(float32 x, float32 y) {
    s_MouseX = x;
    s_MouseY = y;
}

void Input::SetMouseScrollDelta(float32 delta) {
    s_ScrollDelta = delta;
}

}
