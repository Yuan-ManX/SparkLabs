#ifndef SPARKAI_CORE_IO_VECTOR_H
#define SPARKAI_CORE_IO_VECTOR_H

#include "Types.h"

namespace SparkLabs {

template<typename T>
class Vector {
public:
    Vector();
    Vector(size_t count, const T& value = T());
    Vector(std::initializer_list<T> init);
    Vector(const Vector& other);
    Vector(Vector&& other) noexcept;
    ~Vector();

    Vector& operator=(const Vector& other);
    Vector& operator=(Vector&& other) noexcept;

    T& operator[](size_t index) { return m_Data[index]; }
    const T& operator[](size_t index) const { return m_Data[index]; }

    T& At(size_t index);
    const T& At(size_t index) const;

    T& Front() { return m_Data[0]; }
    const T& Front() const { return m_Data[0]; }

    T& Back() { return m_Data[m_Size - 1]; }
    const T& Back() const { return m_Data[m_Size - 1]; }

    T* Data() { return m_Data; }
    const T* Data() const { return m_Data; }

    size_t Size() const { return m_Size; }
    bool Empty() const { return m_Size == 0; }

    void Reserve(size_t newCapacity);
    void Resize(size_t newSize, const T& value = T());
    void Clear();

    void PushBack(const T& value);
    void PushBack(T&& value);
    template<typename... Args> void EmplaceBack(Args&&... args);
    void PopBack();
    void Erase(size_t index);

    bool Contains(const T& value) const;
    size_t IndexOf(const T& value) const;
    void Swap(Vector<T>& other);

    using Iterator = T*;
    using ConstIterator = const T*;
    Iterator Begin() { return m_Data; }
    ConstIterator Begin() const { return m_Data; }
    Iterator End() { return m_Data + m_Size; }
    ConstIterator End() const { return m_Data + m_Size; }

private:
    T* m_Data;
    size_t m_Size;
    size_t m_Capacity;
};

template<typename T>
Vector<T>::Vector() : m_Data(nullptr), m_Size(0), m_Capacity(0) {}

template<typename T>
Vector<T>::Vector(size_t count, const T& value) {
    if (count > 0) {
        m_Data = new T[count];
        m_Capacity = count;
        m_Size = count;
        for (size_t i = 0; i < count; ++i) m_Data[i] = value;
    } else {
        m_Data = nullptr;
        m_Size = 0;
        m_Capacity = 0;
    }
}

template<typename T>
Vector<T>::Vector(std::initializer_list<T> init) {
    m_Size = init.size();
    m_Capacity = m_Size;
    if (m_Size > 0) {
        m_Data = new T[m_Size];
        size_t i = 0;
        for (const auto& item : init) m_Data[i++] = item;
    } else {
        m_Data = nullptr;
        m_Capacity = 0;
    }
}

template<typename T>
Vector<T>::Vector(const Vector& other) : m_Data(nullptr), m_Size(0), m_Capacity(0) {
    if (other.m_Size > 0) {
        m_Data = new T[other.m_Size];
        m_Capacity = other.m_Size;
        m_Size = other.m_Size;
        for (size_t i = 0; i < m_Size; ++i) m_Data[i] = other.m_Data[i];
    }
}

template<typename T>
Vector<T>::Vector(Vector&& other) noexcept : m_Data(other.m_Data), m_Size(other.m_Size), m_Capacity(other.m_Capacity) {
    other.m_Data = nullptr;
    other.m_Size = 0;
    other.m_Capacity = 0;
}

template<typename T>
Vector<T>::~Vector() { delete[] m_Data; }

template<typename T>
Vector<T>& Vector<T>::operator=(const Vector& other) {
    if (this != &other) {
        delete[] m_Data;
        m_Size = other.m_Size;
        if (m_Size > 0) {
            m_Capacity = m_Size;
            m_Data = new T[m_Size];
            for (size_t i = 0; i < m_Size; ++i) m_Data[i] = other.m_Data[i];
        } else {
            m_Data = nullptr;
            m_Capacity = 0;
        }
    }
    return *this;
}

template<typename T>
Vector<T>& Vector<T>::operator=(Vector&& other) noexcept {
    if (this != &other) {
        delete[] m_Data;
        m_Data = other.m_Data;
        m_Size = other.m_Size;
        m_Capacity = other.m_Capacity;
        other.m_Data = nullptr;
        other.m_Size = 0;
        other.m_Capacity = 0;
    }
    return *this;
}

template<typename T>
T& Vector<T>::At(size_t index) {
    return m_Data[index < m_Size ? index : 0];
}

template<typename T>
const T& Vector<T>::At(size_t index) const {
    return m_Data[index < m_Size ? index : 0];
}

template<typename T>
void Vector<T>::Reserve(size_t newCapacity) {
    if (newCapacity > m_Capacity) {
        T* newData = new T[newCapacity];
        for (size_t i = 0; i < m_Size; ++i) newData[i] = m_Data[i];
        delete[] m_Data;
        m_Data = newData;
        m_Capacity = newCapacity;
    }
}

template<typename T>
void Vector<T>::Resize(size_t newSize, const T& value) {
    if (newSize > m_Capacity) Reserve(newSize);
    for (size_t i = m_Size; i < newSize; ++i) m_Data[i] = value;
    m_Size = newSize;
}

template<typename T>
void Vector<T>::Clear() { m_Size = 0; }

template<typename T>
void Vector<T>::PushBack(const T& value) {
    if (m_Size >= m_Capacity) {
        size_t newCapacity = (m_Capacity == 0) ? 4 : m_Capacity * 2;
        Reserve(newCapacity);
    }
    m_Data[m_Size++] = value;
}

template<typename T>
void Vector<T>::PushBack(T&& value) {
    if (m_Size >= m_Capacity) {
        size_t newCapacity = (m_Capacity == 0) ? 4 : m_Capacity * 2;
        Reserve(newCapacity);
    }
    m_Data[m_Size++] = std::move(value);
}

template<typename T>
template<typename... Args>
void Vector<T>::EmplaceBack(Args&&... args) {
    if (m_Size >= m_Capacity) {
        size_t newCapacity = (m_Capacity == 0) ? 4 : m_Capacity * 2;
        Reserve(newCapacity);
    }
    m_Data[m_Size++] = T(std::forward<Args>(args)...);
}

template<typename T>
void Vector<T>::PopBack() { if (m_Size > 0) --m_Size; }

template<typename T>
void Vector<T>::Erase(size_t index) {
    if (index < m_Size) {
        for (size_t i = index; i < m_Size - 1; ++i) m_Data[i] = m_Data[i + 1];
        --m_Size;
    }
}

template<typename T>
bool Vector<T>::Contains(const T& value) const {
    for (size_t i = 0; i < m_Size; ++i) if (m_Data[i] == value) return true;
    return false;
}

template<typename T>
size_t Vector<T>::IndexOf(const T& value) const {
    for (size_t i = 0; i < m_Size; ++i) if (m_Data[i] == value) return i;
    return SIZE_MAX;
}

template<typename T>
void Vector<T>::Swap(Vector<T>& other) {
    T* tempData = m_Data;
    size_t tempSize = m_Size;
    size_t tempCapacity = m_Capacity;
    m_Data = other.m_Data;
    m_Size = other.m_Size;
    m_Capacity = other.m_Capacity;
    other.m_Data = tempData;
    other.m_Size = tempSize;
    other.m_Capacity = tempCapacity;
}

}

#endif