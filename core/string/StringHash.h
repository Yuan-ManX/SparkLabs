#ifndef SPARKAI_CORE_STRING_STRINGHASH_H
#define SPARKAI_CORE_STRING_STRINGHASH_H

#include "Types.h"

namespace SparkLabs {

class StringHash {
public:
    StringHash();
    explicit StringHash(uint32 hash);
    explicit StringHash(const char* str);
    StringHash(const StringHash& other);

    StringHash& operator=(const StringHash& other);

    bool operator==(const StringHash& other) const;
    bool operator!=(const StringHash& other) const;
    bool operator<(const StringHash& other) const;

    uint32 GetHash() const;
    bool IsValid() const;

    static uint32 CalculateFNV1a(const char* str);
    static uint32 CalculateFNV1a(const char* str, int32 length);

    static const StringHash Empty;

private:
    uint32 m_Hash;
};

}

#endif
