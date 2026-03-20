#include "AIMemory.h"

namespace SparkLabs {

AIMemory::AIMemory()
    : m_ShortTermCapacity(10)
{
}

AIMemory::~AIMemory() {
}

void AIMemory::Remember(const String& content, float32 importance) {
    MemorySlot slot;
    slot.content = content;
    slot.importance = importance;
    slot.timestamp = 0.0;
    m_ShortTerm.PushBack(slot);

    if (m_ShortTerm.Size() > (size_t)m_ShortTermCapacity) {
        Consolidate();
    }
}

Vector<MemorySlot> AIMemory::Recall(const String& query, int32 maxResults) {
    return Vector<MemorySlot>();
}

void AIMemory::SetShortTermCapacity(int32 capacity) {
    m_ShortTermCapacity = capacity;
}

void AIMemory::Consolidate() {
    if (m_ShortTerm.Empty()) return;

    MemorySlot mostImportant = m_ShortTerm[0];
    for (auto& slot : m_ShortTerm) {
        if (slot.importance > mostImportant.importance) {
            mostImportant = slot;
        }
    }

    m_LongTerm.PushBack(mostImportant);
    m_ShortTerm.Clear();
}

float32 AIMemory::CalculateImportance(const String& content) {
    return 0.5f;
}

}
