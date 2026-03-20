#pragma once

#include "../core/Types.h"
#include "../core/string/String.h"
#include "../core/Threading/Signal.h"

namespace SparkLabs {

class Window {
public:
    Window();
    Window(const String& title, int32 width, int32 height);
    virtual ~Window();

    virtual void SetTitle(const String& title);
    virtual void SetSize(int32 width, int32 height);
    virtual void SetPosition(int32 x, int32 y);
    virtual void Minimize();
    virtual void Maximize();
    virtual void Restore();
    virtual void Show();
    virtual void Hide();
    virtual void SetFullscreen(bool fullscreen);
    virtual void* GetNativeHandle() const;

    const String& GetTitle() const { return m_Title; }
    int32 GetWidth() const { return m_Width; }
    int32 GetHeight() const { return m_Height; }
    int32 GetX() const { return m_X; }
    int32 GetY() const { return m_Y; }
    bool IsFullscreen() const { return m_Fullscreen; }
    bool IsVisible() const { return m_Visible; }
    bool IsFocused() const { return m_Focused; }
    bool IsMinimized() const { return m_Minimized; }
    bool IsMaximized() const { return m_Maximized; }

    Signal<int32, int32> OnResized;
    Signal<int32, int32> OnMoved;
    Signal<bool> OnFocusChanged;
    Signal<void> OnClose;

    virtual void ProcessEvents();
    virtual void SwapBuffers();

    static Window* GetMainWindow();
    static void SetMainWindow(Window* window);

protected:
    String m_Title;
    int32 m_Width;
    int32 m_Height;
    int32 m_X;
    int32 m_Y;
    bool m_Fullscreen;
    bool m_Visible;
    bool m_Focused;
    bool m_Minimized;
    bool m_Maximized;
    void* m_NativeHandle;

    static Window* s_MainWindow;
};

}
