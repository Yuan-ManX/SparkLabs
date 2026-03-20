#ifndef SPARKAI_AI_BRAIN_TENSORREF_H
#define SPARKAI_AI_BRAIN_TENSORREF_H

#include "../../core/Types.h"
#include "../../core/io/Vector.h"
#include <cstring>

namespace SparkLabs {

enum class DataType {
    Float32,
    Float64,
    Int32,
    Int64,
    UInt8,
    Bool
};

struct TensorShape {
    Vector<int32> dims;

    TensorShape() {}
    TensorShape(const Vector<int32>& dimensions) : dims(dimensions) {}

    int32 NumDims() const { return static_cast<int32>(dims.Size()); }
    size_t NumElements() const {
        size_t count = 1;
        for (int32 i = 0; i < dims.Size(); ++i) {
            count *= dims[i];
        }
        return count;
    }
};

class TensorRef {
public:
    TensorRef();
    TensorRef(void* data, const TensorShape& shape, DataType dataType);
    TensorRef(const TensorRef& other);
    TensorRef(TensorRef&& other) noexcept;
    ~TensorRef();

    TensorRef& operator=(const TensorRef& other);
    TensorRef& operator=(TensorRef&& other) noexcept;

    void* GetData() { return m_Data; }
    const void* GetData() const { return m_Data; }

    TensorShape GetShape() const { return m_Shape; }
    DataType GetDataType() const { return m_DataType; }
    size_t GetNumElements() const { return m_Shape.NumElements(); }

    template<typename T>
    T* GetDataAs() { return static_cast<T*>(m_Data); }

    template<typename T>
    const T* GetDataAs() const { return static_cast<const T*>(m_Data); }

    size_t GetByteSize() const;
    TensorRef Slice(const Vector<int32>& start, const Vector<int32>& end) const;

    bool IsValid() const { return m_Data != nullptr; }
    operator bool() const { return m_Data != nullptr; }

    void Reset();

private:
    void* m_Data;
    TensorShape m_Shape;
    DataType m_DataType;
    bool m_OwnsData;
};

inline TensorRef::TensorRef()
    : m_Data(nullptr)
    , m_DataType(DataType::Float32)
    , m_OwnsData(false) {
}

inline TensorRef::TensorRef(void* data, const TensorShape& shape, DataType dataType)
    : m_Data(data)
    , m_Shape(shape)
    , m_DataType(dataType)
    , m_OwnsData(false) {
}

inline TensorRef::TensorRef(const TensorRef& other)
    : m_Data(other.m_Data)
    , m_Shape(other.m_Shape)
    , m_DataType(other.m_DataType)
    , m_OwnsData(false) {
}

inline TensorRef::TensorRef(TensorRef&& other) noexcept
    : m_Data(other.m_Data)
    , m_Shape(other.m_Shape)
    , m_DataType(other.m_DataType)
    , m_OwnsData(other.m_OwnsData) {
    other.m_Data = nullptr;
    other.m_OwnsData = false;
}

inline TensorRef::~TensorRef() {
    if (m_OwnsData && m_Data) {
        delete[] static_cast<uint8*>(m_Data);
    }
}

inline TensorRef& TensorRef::operator=(const TensorRef& other) {
    if (this != &other) {
        if (m_OwnsData && m_Data) {
            delete[] static_cast<uint8*>(m_Data);
        }
        m_Data = other.m_Data;
        m_Shape = other.m_Shape;
        m_DataType = other.m_DataType;
        m_OwnsData = false;
    }
    return *this;
}

inline TensorRef& TensorRef::operator=(TensorRef&& other) noexcept {
    if (this != &other) {
        if (m_OwnsData && m_Data) {
            delete[] static_cast<uint8*>(m_Data);
        }
        m_Data = other.m_Data;
        m_Shape = other.m_Shape;
        m_DataType = other.m_DataType;
        m_OwnsData = other.m_OwnsData;
        other.m_Data = nullptr;
        other.m_OwnsData = false;
    }
    return *this;
}

inline size_t TensorRef::GetByteSize() const {
    size_t elementSize = 4;
    switch (m_DataType) {
        case DataType::Float32: elementSize = 4; break;
        case DataType::Float64: elementSize = 8; break;
        case DataType::Int32: elementSize = 4; break;
        case DataType::Int64: elementSize = 8; break;
        case DataType::UInt8: elementSize = 1; break;
        case DataType::Bool: elementSize = 1; break;
    }
    return GetNumElements() * elementSize;
}

inline TensorRef TensorRef::Slice(const Vector<int32>& start, const Vector<int32>& end) const {
    TensorRef result;
    result.m_Shape = m_Shape;
    result.m_DataType = m_DataType;
    result.m_OwnsData = false;
    result.m_Data = m_Data;
    (void)start;
    (void)end;
    return result;
}

inline void TensorRef::Reset() {
    if (m_OwnsData && m_Data) {
        delete[] static_cast<uint8*>(m_Data);
    }
    m_Data = nullptr;
    m_Shape.dims.Clear();
    m_OwnsData = false;
}

}

#endif