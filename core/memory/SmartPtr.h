#ifndef SPARKAI_CORE_MEMORY_SMARTPTR_H
#define SPARKAI_CORE_MEMORY_SMARTPTR_H

#include "Types.h"

namespace SparkLabs {

class RefCount {
public:
    RefCount();
    void AddRef();
    void Release();
    int32 UseCount() const;
private:
    int32 m_Count;
};

template<typename T>
class WeakPtr;

template<typename T>
class SmartPtr {
public:
    SmartPtr() : m_Pointer(nullptr), m_RefCount(nullptr) {}
    SmartPtr(std::nullptr_t) : m_Pointer(nullptr), m_RefCount(nullptr) {}
    SmartPtr(T* pointer);
    SmartPtr(const SmartPtr& other);
    template<typename U> SmartPtr(const SmartPtr<U>& other);
    SmartPtr(SmartPtr&& other) noexcept;
    ~SmartPtr();

    SmartPtr& operator=(std::nullptr_t);
    SmartPtr& operator=(const SmartPtr& other);
    SmartPtr& operator=(SmartPtr&& other) noexcept;

    T* operator->() const { return m_Pointer; }
    T& operator*() const { return *m_Pointer; }
    operator bool() const { return m_Pointer != nullptr; }
    bool operator==(const SmartPtr& other) const { return m_Pointer == other.m_Pointer; }
    bool operator==(std::nullptr_t) const { return m_Pointer == nullptr; }
    bool operator!=(const SmartPtr& other) const { return m_Pointer != other.m_Pointer; }
    bool operator!=(std::nullptr_t) const { return m_Pointer != nullptr; }

    T* Get() const { return m_Pointer; }
    RefCount* GetRefCount() const { return m_RefCount; }
    void Reset();

    template<typename U>
    static SmartPtr<T> StaticCast(const SmartPtr<U>& other);

private:
    void Release();
    T* m_Pointer;
    RefCount* m_RefCount;

    template<typename U>
    friend class SmartPtr;

    template<typename U>
    friend class WeakPtr;
};

template<typename T>
class WeakPtr {
public:
    WeakPtr() : m_Pointer(nullptr), m_RefCount(nullptr) {}
    WeakPtr(std::nullptr_t) : m_Pointer(nullptr), m_RefCount(nullptr) {}
    WeakPtr(const SmartPtr<T>& smart);
    WeakPtr(const WeakPtr& other);
    template<typename U> WeakPtr(const WeakPtr<U>& other);
    WeakPtr(WeakPtr&& other) noexcept;
    ~WeakPtr();

    WeakPtr& operator=(std::nullptr_t);
    WeakPtr& operator=(const WeakPtr& other);
    WeakPtr& operator=(WeakPtr&& other) noexcept;

    SmartPtr<T> Lock() const;
    operator bool() const;
    bool Expired() const { return !m_RefCount || m_RefCount->UseCount() == 0; }
    T* operator->() const { return m_Pointer; }
    T& operator*() const { return *m_Pointer; }
    T* Get() const { return m_Pointer; }

private:
    void AddRef();
    void Release();
    T* m_Pointer;
    RefCount* m_RefCount;

    template<typename U>
    friend class SmartPtr;
};

template<typename T, typename... Args>
SmartPtr<T> MakeSmartPtr(Args&&... args);

template<typename T>
template<typename U>
SmartPtr<T> SmartPtr<T>::StaticCast(const SmartPtr<U>& other) {
    SmartPtr<T> result;
    result.m_Pointer = static_cast<T*>(other.m_Pointer);
    result.m_RefCount = other.m_RefCount;
    if (result.m_RefCount) result.m_RefCount->AddRef();
    return result;
}

template<typename T>
SmartPtr<T>::SmartPtr(T* pointer) : m_Pointer(pointer), m_RefCount(nullptr) {
    if (m_Pointer) {
        m_RefCount = new RefCount();
        m_RefCount->AddRef();
    }
}

template<typename T>
SmartPtr<T>::SmartPtr(const SmartPtr& other) : m_Pointer(other.m_Pointer), m_RefCount(other.m_RefCount) {
    if (m_RefCount) m_RefCount->AddRef();
}

template<typename T>
template<typename U>
SmartPtr<T>::SmartPtr(const SmartPtr<U>& other) : m_Pointer(other.m_Pointer), m_RefCount(other.m_RefCount) {
    if (m_RefCount) m_RefCount->AddRef();
}

template<typename T>
SmartPtr<T>::SmartPtr(SmartPtr&& other) noexcept : m_Pointer(other.m_Pointer), m_RefCount(other.m_RefCount) {
    other.m_Pointer = nullptr;
    other.m_RefCount = nullptr;
}

template<typename T>
SmartPtr<T>::~SmartPtr() {
    Release();
}

template<typename T>
SmartPtr<T>& SmartPtr<T>::operator=(std::nullptr_t) {
    Release();
    m_Pointer = nullptr;
    m_RefCount = nullptr;
    return *this;
}

template<typename T>
SmartPtr<T>& SmartPtr<T>::operator=(const SmartPtr& other) {
    if (this != &other) {
        Release();
        m_Pointer = other.m_Pointer;
        m_RefCount = other.m_RefCount;
        if (m_RefCount) m_RefCount->AddRef();
    }
    return *this;
}

template<typename T>
SmartPtr<T>& SmartPtr<T>::operator=(SmartPtr&& other) noexcept {
    if (this != &other) {
        Release();
        m_Pointer = other.m_Pointer;
        m_RefCount = other.m_RefCount;
        other.m_Pointer = nullptr;
        other.m_RefCount = nullptr;
    }
    return *this;
}

template<typename T>
void SmartPtr<T>::Reset() {
    Release();
    m_Pointer = nullptr;
    m_RefCount = nullptr;
}

template<typename T>
void SmartPtr<T>::Release() {
    if (m_RefCount && m_RefCount->Release()) {
        delete m_Pointer;
        delete m_RefCount;
    }
}

template<typename T>
WeakPtr<T>::WeakPtr(const SmartPtr<T>& smart) : m_Pointer(smart.m_Pointer), m_RefCount(smart.m_RefCount) {
    if (m_RefCount) m_RefCount->AddRef();
}

template<typename T>
WeakPtr<T>::WeakPtr(const WeakPtr& other) : m_Pointer(other.m_Pointer), m_RefCount(other.m_RefCount) {
    if (m_RefCount) m_RefCount->AddRef();
}

template<typename T>
template<typename U>
WeakPtr<T>::WeakPtr(const WeakPtr<U>& other) : m_Pointer(other.m_Pointer), m_RefCount(other.m_RefCount) {
    if (m_RefCount) m_RefCount->AddRef();
}

template<typename T>
WeakPtr<T>::WeakPtr(WeakPtr&& other) noexcept : m_Pointer(other.m_Pointer), m_RefCount(other.m_RefCount) {
    other.m_Pointer = nullptr;
    other.m_RefCount = nullptr;
}

template<typename T>
WeakPtr<T>::~WeakPtr() {
    Release();
}

template<typename T>
WeakPtr<T>& WeakPtr<T>::operator=(std::nullptr_t) {
    Release();
    m_Pointer = nullptr;
    m_RefCount = nullptr;
    return *this;
}

template<typename T>
WeakPtr<T>& WeakPtr<T>::operator=(const WeakPtr& other) {
    if (this != &other) {
        Release();
        m_Pointer = other.m_Pointer;
        m_RefCount = other.m_RefCount;
        if (m_RefCount) m_RefCount->AddRef();
    }
    return *this;
}

template<typename T>
WeakPtr<T>& WeakPtr<T>::operator=(WeakPtr&& other) noexcept {
    if (this != &other) {
        Release();
        m_Pointer = other.m_Pointer;
        m_RefCount = other.m_RefCount;
        other.m_Pointer = nullptr;
        other.m_RefCount = nullptr;
    }
    return *this;
}

template<typename T>
SmartPtr<T> WeakPtr<T>::Lock() const {
    if (m_RefCount && m_RefCount->UseCount() > 0) {
        return SmartPtr<T>(*this);
    }
    return SmartPtr<T>(nullptr);
}

template<typename T>
WeakPtr<T>::operator bool() const {
    if (!m_RefCount) return false;
    return m_RefCount->UseCount() > 0 && m_Pointer != nullptr;
}

template<typename T>
void WeakPtr<T>::AddRef() {
    if (m_RefCount) m_RefCount->AddRef();
}

template<typename T>
void WeakPtr<T>::Release() {
    if (m_RefCount && m_RefCount->Release()) {
        delete m_RefCount;
    }
}

template<typename T, typename... Args>
SmartPtr<T> MakeSmartPtr(Args&&... args) {
    return SmartPtr<T>(new T(std::forward<Args>(args)...));
}

template<typename T>
template<typename U>
SmartPtr<T> DynamicCast(const SmartPtr<U>& other) {
    T* ptr = dynamic_cast<T*>(other.Get());
    if (ptr) {
        SmartPtr<T> result;
        result.m_Pointer = ptr;
        result.m_RefCount = other.GetRefCount();
        if (result.m_RefCount) result.m_RefCount->AddRef();
        return result;
    }
    return SmartPtr<T>(nullptr);
}

}

#endif