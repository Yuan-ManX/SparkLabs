#include "memory/SmartPtr.h"

namespace SparkLabs {

RefCount::RefCount() : m_Count(0) {
}

void RefCount::AddRef() {
    ++m_Count;
}

void RefCount::Release() {
    --m_Count;
}

int32 RefCount::UseCount() const {
    return m_Count;
}

}
