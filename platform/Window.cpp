#include "Window.h"

namespace SparkLabs {

Window* Window::s_MainWindow = nullptr;

Window::Window()
    : m_Title("SparkLabs Window")
    , m_Width(1280)
    , m_Height(720)
    , m_X(100)
    , m_Y(100)
    , m_Fullscreen(false)
    , m_Visible(true)
    , m_Focused(true)
    , m_Minimized(false)
    , m_Maximized(false)
    , m_NativeHandle(nullptr) {
}

Window::Window(const String& title, int32 width, int32 height)
    : m_Title(title)
    , m_Width(width)
    , m_Height(height)
    , m_X(100)
    , m_Y(100)
    , m_Fullscreen(false)
    , m_Visible(true)
    , m_Focused(true)
    , m_Minimized(false)
    , m_Maximized(false)
    , m_NativeHandle(nullptr) {
}

Window::~Window() {
    if (s_MainWindow == this) {
        s_MainWindow = nullptr;
    }
}

void Window::SetTitle(const String& title) {
    m_Title = title;
}

void Window::SetSize(int32 width, int32 height) {
    if (m_Width != width || m_Height != height) {
        m_Width = width;
        m_Height = height;
        OnResized.Emit(m_Width, m_Height);
    }
}

void Window::SetPosition(int32 x, int32 y) {
    if (m_X != x || m_Y != y) {
        m_X = x;
        m_Y = y;
        OnMoved.Emit(m_X, m_Y);
    }
}

void Window::Minimize() {
    if (!m_Minimized) {
        m_Minimized = true;
        m_Maximized = false;
    }
}

void Window::Maximize() {
    if (!m_Maximized) {
        m_Maximized = true;
        m_Minimized = false;
    }
}

void Window::Restore() {
    m_Minimized = false;
    m_Maximized = false;
}

void Window::Show() {
    if (!m_Visible) {
        m_Visible = true;
    }
}

void Window::Hide() {
    if (m_Visible) {
        m_Visible = false;
    }
}

void Window::SetFullscreen(bool fullscreen) {
    if (m_Fullscreen != fullscreen) {
        m_Fullscreen = fullscreen;
        if (fullscreen) {
            m_Minimized = false;
            m_Maximized = false;
        }
    }
}

void* Window::GetNativeHandle() const {
    return m_NativeHandle;
}

void Window::ProcessEvents() {
}

void Window::SwapBuffers() {
}

Window* Window::GetMainWindow() {
    return s_MainWindow;
}

void Window::SetMainWindow(Window* window) {
    s_MainWindow = window;
}

}
