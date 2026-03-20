#pragma once

#include "../../core/Types.h"
#include "../../core/io/Vector.h"
#include "../../core/string/String.h"

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/session/onnxruntime_cxx_api.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED
using OrtValue = Ort::Value;
#else
using OrtValue = void;
#endif

class Tensor {
public:
    enum class DataType {
        Float32,
        Float64,
        Int32,
        Int64,
        UInt8,
        Int8,
        UInt16,
        Int16,
        Bool
    };

    Tensor();
    Tensor(DataType dtype);
    Tensor(const Vector<size_t>& shape, DataType dtype);
    Tensor(const Tensor& other);
    Tensor(Tensor&& other) noexcept;
    ~Tensor();

    Tensor& operator=(const Tensor& other);
    Tensor& operator=(Tensor&& other) noexcept;

    template<typename T>
    T* GetData();

    template<typename T>
    const T* GetData() const;

    template<typename T>
    void SetData(const Vector<T>& data, const Vector<size_t>& shape);

    void SetDataRaw(const Vector<uint8_t>& data, const Vector<size_t>& shape, DataType dtype);

    Tensor Clone() const;

    void Reshape(const Vector<size_t>& newShape);

    float32 AsFloat(size_t index) const;
    void SetFloat(float32 value, size_t index);

    int64 AsInt(size_t index) const;
    void SetInt(int64 value, size_t index);

    const Vector<size_t>& GetShape() const { return m_Shape; }
    DataType GetDataType() const { return m_DataType; }
    size_t GetSize() const { return m_Size; }
    size_t GetNumElements() const { return m_NumElements; }
    size_t GetNumBytes() const { return m_Data.Size(); }
    bool IsGPU() const { return m_IsGPU; }
    void SetGPU(bool isGPU) { m_IsGPU = isGPU; }

    static size_t GetDataTypeSize(DataType dtype);
    static size_t GetElementSize(DataType dtype);

private:
    Vector<size_t> m_Shape;
    DataType m_DataType;
    Vector<uint8_t> m_Data;
    size_t m_NumElements;
    bool m_IsGPU;
};

using TensorRef = Tensor*;

template<typename T>
T* Tensor::GetData() {
    if (m_Data.Empty()) return nullptr;
    return reinterpret_cast<T*>(m_Data.Data());
}

template<typename T>
const T* Tensor::GetData() const {
    if (m_Data.Empty()) return nullptr;
    return reinterpret_cast<const T*>(m_Data.Data());
}

template<typename T>
void Tensor::SetData(const Vector<T>& data, const Vector<size_t>& shape) {
    m_Shape = shape;
    m_NumElements = 1;
    for (size_t i = 0; i < shape.Size(); ++i) {
        m_NumElements *= shape[i];
    }

    size_t numBytes = m_NumElements * sizeof(T);
    m_Data.Resize(numBytes);
    std::memcpy(m_Data.Data(), data.Data(), numBytes);
}

}
