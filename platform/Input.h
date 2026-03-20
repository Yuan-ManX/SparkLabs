#pragma once

#include "../core/Types.h"
#include "../core/math/Vector2.h"

namespace SparkLabs {

class Input {
public:
    enum class KeyCode {
        Unknown = 0,

        A = 4,
        B = 5,
        C = 6,
        D = 7,
        E = 8,
        F = 9,
        G = 10,
        H = 11,
        I = 12,
        J = 13,
        K = 14,
        L = 15,
        M = 16,
        N = 17,
        O = 18,
        P = 19,
        Q = 20,
        R = 21,
        S = 22,
        T = 23,
        U = 24,
        V = 25,
        W = 26,
        X = 27,
        Y = 28,
        Z = 29,

        Num0 = 30,
        Num1 = 31,
        Num2 = 32,
        Num3 = 33,
        Num4 = 34,
        Num5 = 35,
        Num6 = 36,
        Num7 = 37,
        Num8 = 38,
        Num9 = 39,

        Numpad0 = 82,
        Numpad1 = 83,
        Numpad2 = 84,
        Numpad3 = 85,
        Numpad4 = 86,
        Numpad5 = 87,
        Numpad6 = 88,
        Numpad7 = 89,
        Numpad8 = 90,
        Numpad9 = 91,
        NumpadMultiply = 85,
        NumpadAdd = 87,
        NumpadSubtract = 86,
        NumpadDecimal = 84,
        NumpadDivide = 84,

        F1 = 58,
        F2 = 59,
        F3 = 60,
        F4 = 61,
        F5 = 62,
        F6 = 63,
        F7 = 64,
        F8 = 65,
        F9 = 66,
        F10 = 67,
        F11 = 68,
        F12 = 69,

        LeftShift = 225,
        RightShift = 229,
        LeftControl = 224,
        RightControl = 228,
        LeftAlt = 226,
        RightAlt = 230,

        Space = 44,
        Enter = 40,
        Escape = 41,
        Tab = 43,
        Backspace = 42,
        Delete = 51,

        Left = 80,
        Right = 79,
        Up = 82,
        Down = 81,

        CapsLock = 57,
        PrintScreen = 70,
        ScrollLock = 71,
        Pause = 72,

        Insert = 73,
        Home = 74,
        End = 77,
        PageUp = 75,
        PageDown = 78
    };

    enum class MouseButton { Left, Right, Middle };

    static bool IsKeyDown(KeyCode key);
    static bool IsKeyPressed(KeyCode key);
    static bool IsMouseButtonDown(MouseButton button);
    static Vector2 GetMousePosition();
    static float32 GetMouseX();
    static float32 GetMouseY();
    static float32 GetMouseScrollDelta();
    static bool IsGamepadConnected(int32 index);
    static Vector2 GetGamepadLeftStick(int32 index);
    static Vector2 GetGamepadRightStick(int32 index);
    static float32 GetGamepadTrigger(int32 index, bool isLeft);

    static void SetMousePosition(float32 x, float32 y);
    static void SetMouseScrollDelta(float32 delta);

    static void Initialize();
    static void Shutdown();
    static void Update();

private:
    static bool s_KeyStates[256];
    static bool s_PrevKeyStates[256];
    static bool s_MouseButtonStates[3];
    static bool s_PrevMouseButtonStates[3];
    static float32 s_MouseX;
    static float32 s_MouseY;
    static float32 s_ScrollDelta;
    static bool s_GamepadConnected[4];
    static Vector2 s_GamepadLeftStick[4];
    static Vector2 s_GamepadRightStick[4];
    static float32 s_GamepadTrigger[4][2];
};

}
