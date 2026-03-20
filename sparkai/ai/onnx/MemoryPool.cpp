#include "MemoryPool.h"
#include <algorithm>

namespace SparkLabs {

MemoryPool::MemoryPool(size_t maxPoolSize)
    : m_MaxPoolSize(maxPoolSize)
    , m_CurrentTime(0) {
}

MemoryPool::~MemoryPool() {
    for (size_t i = 0; i < m_Pool.Size(); ++i) {
        if (m_Pool[i].tensor != nullptr) {
            delete m_Pool[i].tensor;
            m_Pool[i].tensor = nullptr;
        }
    }
    m_Pool.Clear();
}

TensorRef MemoryPool::Allocate(const Vector<size_t>& shape, Tensor::DataType dtype) {
    m_CurrentTime++;

    for (size_t i = 0; i < m_Pool.Size(); ++i) {
        if (!m_Pool[i].inUse && m_Pool[i].tensor != nullptr) {
            if (m_Pool[i].tensor->GetShape() == shape &&
                m_Pool[i].tensor->GetDataType() == dtype) {
                m_Pool[i].inUse = true;
                m_Pool[i].lastUsed = m_CurrentTime;
                return m_Pool[i].tensor;
            }
        }
    }

    if (m_Pool.Size() < m_MaxPoolSize) {
        PooledTensor entry;
        entry.tensor = new Tensor(shape, dtype);
        entry.lastUsed = m_CurrentTime;
        entry.inUse = true;
        m_Pool.EmplaceBack(entry);
        return entry.tensor;
    }

    for (size_t i = 0; i < m_Pool.Size(); ++i) {
        if (!m_Pool[i].inUse) {
            delete m_Pool[i].tensor;
            m_Pool[i].tensor = new Tensor(shape, dtype);
            m_Pool[i].lastUsed = m_CurrentTime;
            m_Pool[i].inUse = true;
            return m_Pool[i].tensor;
        }
    }

    return nullptr;
}

void MemoryPool::Release(TensorRef& tensor) {
    if (tensor == nullptr) return;

    for (size_t i = 0; i < m_Pool.Size(); ++i) {
        if (m_Pool[i].tensor == tensor) {
            m_Pool[i].inUse = false;
            m_Pool[i].lastUsed = m_CurrentTime;
            tensor = nullptr;
            return;
        }
    }

    delete tensor;
    tensor = nullptr;
}

void MemoryPool::GC() {
    m_CurrentTime++;

    uint64_t threshold = m_CurrentTime > 60 ? m_CurrentTime - 60 : 0;

    for (size_t i = 0; i < m_Pool.Size(); ) {
        if (!m_Pool[i].inUse && m_Pool[i].lastUsed < threshold) {
            delete m_Pool[i].tensor;
            m_Pool.Erase(i);
        } else {
            ++i;
        }
    }
}

size_t MemoryPool::GetAvailableCount() const {
    size_t count = 0;
    for (size_t i = 0; i < m_Pool.Size(); ++i) {
        if (!m_Pool[i].inUse) {
            count++;
        }
    }
    return count;
}

void MemoryPool::UpdatePoolEntry(size_t index) {
    if (index < m_Pool.Size()) {
        m_Pool[index].lastUsed = m_CurrentTime;
    }
}

TensorRef MemoryPool::FindOrCreateTensor(const Vector<size_t>& shape, Tensor::DataType dtype) {
    for (size_t i = 0; i < m_Pool.Size(); ++i) {
        if (!m_Pool[i].inUse && m_Pool[i].tensor != nullptr) {
            if (m_Pool[i].tensor->GetShape() == shape &&
                m_Pool[i].tensor->GetDataType() == dtype) {
                m_Pool[i].inUse = true;
                m_Pool[i].lastUsed = m_CurrentTime;
                return m_Pool[i].tensor;
            }
        }
    }

    if (m_Pool.Size() < m_MaxPoolSize) {
        PooledTensor entry;
        entry.tensor = new Tensor(shape, dtype);
        entry.lastUsed = m_CurrentTime;
        entry.inUse = true;
        m_Pool.EmplaceBack(entry);
        return entry.tensor;
    }

    return nullptr;
}

}
