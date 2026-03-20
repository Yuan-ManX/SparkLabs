#pragma once

#include "../../core/Types.h"
#include "Tensor.h"

namespace SparkLabs {

class MemoryPool {
public:
    struct PooledTensor {
        TensorRef tensor;
        uint64_t lastUsed;
        bool inUse;
    };

    MemoryPool(size_t maxPoolSize = 256);
    ~MemoryPool();

    TensorRef Allocate(const Vector<size_t>& shape, Tensor::DataType dtype);
    void Release(TensorRef& tensor);
    void GC();

    size_t GetPoolSize() const { return m_Pool.Size(); }
    size_t GetMaxPoolSize() const { return m_MaxPoolSize; }
    size_t GetAvailableCount() const;

private:
    Vector<PooledTensor> m_Pool;
    size_t m_MaxPoolSize;
    uint64_t m_CurrentTime;
    TensorRef FindOrCreateTensor(const Vector<size_t>& shape, Tensor::DataType dtype);
    void UpdatePoolEntry(size_t index);
};

}
