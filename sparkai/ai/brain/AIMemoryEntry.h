#ifndef SPARKAI_AI_BRAIN_AIMEMORYENTRY_H
#define SPARKAI_AI_BRAIN_AIMEMORYENTRY_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"

namespace SparkLabs {

enum class MemoryType {
    ShortTerm,
    LongTerm,
    Episodic,
    Semantic
};

struct AIMemoryEntry {
    String content;
    Vector<float32> embedding;
    float64 importance;
    float64 timestamp;
    float64 expiresAt;
    MemoryType type;

    AIMemoryEntry()
        : importance(0.0)
        , timestamp(0.0)
        , expiresAt(0.0)
        , type(MemoryType::ShortTerm) {
    }

    bool IsExpired() const {
        return expiresAt > 0.0 && timestamp >= expiresAt;
    }

    bool HasEmbedding() const {
        return !embedding.Empty();
    }
};

}

#endif