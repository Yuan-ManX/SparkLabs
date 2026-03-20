#ifndef SPARKLABS_ENGINE_NPC_AIMEMORY_H
#define SPARKLABS_ENGINE_NPC_AIMEMORY_H

#include <Object.h>
#include <SmartPtr.h>
#include <Vector.h>
#include <String.h>

namespace SparkLabs {

struct MemorySlot {
    String content;
    float32 importance;
    float64 timestamp;
    Vector<float32> embedding;
};

class AIMemory : public Object {
    SPARKLABS_OBJECT(AIMemory)
public:
    enum class MemoryType {
        ShortTerm,
        LongTerm,
        Episodic,
        Semantic
    };

    AIMemory();
    virtual ~AIMemory();

    void Remember(const String& content, float32 importance);
    Vector<MemorySlot> Recall(const String& query, int32 maxResults = 5);

    void SetShortTermCapacity(int32 capacity);
    void Consolidate();

    float32 CalculateImportance(const String& content);

private:
    Vector<MemorySlot> m_ShortTerm;
    Vector<MemorySlot> m_LongTerm;
    int32 m_ShortTermCapacity;
};

}

#endif
