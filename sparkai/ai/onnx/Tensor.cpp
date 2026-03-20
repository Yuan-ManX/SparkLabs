#include "Tensor.h"
#include <cstring>

namespace SparkLabs {

Tensor::Tensor()
    : m_DataType(DataType::Float32)
    , m_NumElements(0)
    , m_IsGPU(false) {
}

Tensor::Tensor(DataType dtype)
    : m_DataType(dtype)
    , m_NumElements(0)
    , m_IsGPU(false) {
}

Tensor::Tensor(const Vector<size_t>& shape, DataType dtype)
    : m_Shape(shape)
    , m_DataType(dtype)
    , m_NumElements(0)
    , m_IsGPU(false) {
    m_NumElements = 1;
    for (size_t i = 0; i < shape.Size(); ++i) {
        m_NumElements *= shape[i];
    }
    size_t numBytes = m_NumElements * GetElementSize(dtype);
    m_Data.Resize(numBytes);
}

Tensor::Tensor(const Tensor& other)
    : m_Shape(other.m_Shape)
    , m_DataType(other.m_DataType)
    , m_Data(other.m_Data)
    , m_NumElements(other.m_NumElements)
    , m_IsGPU(other.m_IsGPU) {
}

Tensor::Tensor(Tensor&& other) noexcept
    : m_Shape(std::move(other.m_Shape))
    , m_DataType(other.m_DataType)
    , m_Data(std::move(other.m_Data))
    , m_NumElements(other.m_NumElements)
    , m_IsGPU(other.m_IsGPU) {
    other.m_NumElements = 0;
    other.m_IsGPU = false;
}

Tensor::~Tensor() {
    m_Shape.Clear();
    m_Data.Clear();
    m_NumElements = 0;
    m_IsGPU = false;
}

Tensor& Tensor::operator=(const Tensor& other) {
    if (this != &other) {
        m_Shape = other.m_Shape;
        m_DataType = other.m_DataType;
        m_Data = other.m_Data;
        m_NumElements = other.m_NumElements;
        m_IsGPU = other.m_IsGPU;
    }
    return *this;
}

Tensor& Tensor::operator=(Tensor&& other) noexcept {
    if (this != &other) {
        m_Shape = std::move(other.m_Shape);
        m_DataType = other.m_DataType;
        m_Data = std::move(other.m_Data);
        m_NumElements = other.m_NumElements;
        m_IsGPU = other.m_IsGPU;
        other.m_NumElements = 0;
        other.m_IsGPU = false;
    }
    return *this;
}

Tensor Tensor::Clone() const {
    Tensor clone;
    clone.m_Shape = m_Shape;
    clone.m_DataType = m_DataType;
    clone.m_Data = m_Data;
    clone.m_NumElements = m_NumElements;
    clone.m_IsGPU = m_IsGPU;
    return clone;
}

void Tensor::Reshape(const Vector<size_t>& newShape) {
    size_t newNumElements = 1;
    for (size_t i = 0; i < newShape.Size(); ++i) {
        newNumElements *= newShape[i];
    }

    if (newNumElements != m_NumElements) {
        return;
    }

    m_Shape = newShape;
}

void Tensor::SetDataRaw(const Vector<uint8_t>& data, const Vector<size_t>& shape, DataType dtype) {
    m_Shape = shape;
    m_DataType = dtype;
    m_NumElements = 1;
    for (size_t i = 0; i < shape.Size(); ++i) {
        m_NumElements *= shape[i];
    }
    m_Data = data;
}

float32 Tensor::AsFloat(size_t index) const {
    if (index >= m_NumElements) return 0.0f;

    switch (m_DataType) {
        case DataType::Float32: {
            const float32* data = GetData<float32>();
            return data[index];
        }
        case DataType::Float64: {
            const float64* data = GetData<float64>();
            return static_cast<float32>(data[index]);
        }
        case DataType::Int32: {
            const int32* data = GetData<int32>();
            return static_cast<float32>(data[index]);
        }
        case DataType::Int64: {
            const int64* data = GetData<int64>();
            return static_cast<float32>(data[index]);
        }
        case DataType::Int8: {
            const int8* data = GetData<int8>();
            return static_cast<float32>(data[index]);
        }
        case DataType::UInt8: {
            const uint8* data = GetData<uint8>();
            return static_cast<float32>(data[index]);
        }
        default:
            return 0.0f;
    }
}

void Tensor::SetFloat(float32 value, size_t index) {
    if (index >= m_NumElements) return;

    switch (m_DataType) {
        case DataType::Float32: {
            float32* data = GetData<float32>();
            data[index] = value;
            break;
        }
        case DataType::Float64: {
            float64* data = GetData<float64>();
            data[index] = static_cast<float64>(value);
            break;
        }
        case DataType::Int32: {
            int32* data = GetData<int32>();
            data[index] = static_cast<int32>(value);
            break;
        }
        case DataType::Int64: {
            int64* data = GetData<int64>();
            data[index] = static_cast<int64>(value);
            break;
        }
        default:
            break;
    }
}

int64 Tensor::AsInt(size_t index) const {
    if (index >= m_NumElements) return 0;

    switch (m_DataType) {
        case DataType::Int32: {
            const int32* data = GetData<int32>();
            return data[index];
        }
        case DataType::Int64: {
            const int64* data = GetData<int64>();
            return data[index];
        }
        case DataType::Float32: {
            const float32* data = GetData<float32>();
            return static_cast<int64>(data[index]);
        }
        case DataType::UInt8: {
            const uint8* data = GetData<uint8>();
            return data[index];
        }
        default:
            return 0;
    }
}

void Tensor::SetInt(int64 value, size_t index) {
    if (index >= m_NumElements) return;

    switch (m_DataType) {
        case DataType::Int32: {
            int32* data = GetData<int32>();
            data[index] = static_cast<int32>(value);
            break;
        }
        case DataType::Int64: {
            int64* data = GetData<int64>();
            data[index] = value;
            break;
        }
        default:
            break;
    }
}

size_t Tensor::GetDataTypeSize(DataType dtype) {
    switch (dtype) {
        case DataType::Float32: return sizeof(float32);
        case DataType::Float64: return sizeof(float64);
        case DataType::Int32: return sizeof(int32);
        case DataType::Int64: return sizeof(int64);
        case DataType::UInt8: return sizeof(uint8);
        case DataType::Int8: return sizeof(int8);
        case DataType::UInt16: return sizeof(uint16);
        case DataType::Int16: return sizeof(int16);
        case DataType::Bool: return sizeof(bool);
        default: return 0;
    }
}

size_t Tensor::GetElementSize(DataType dtype) {
    return GetDataTypeSize(dtype);
}

}
