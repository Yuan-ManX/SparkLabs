#include "string/StringHash.h"

namespace SparkLabs {

const StringHash StringHash::Empty(0);

StringHash::StringHash() : m_Hash(0) {
}

StringHash::StringHash(uint32 hash) : m_Hash(hash) {
}

StringHash::StringHash(const char* str) : m_Hash(CalculateFNV1a(str)) {
}

StringHash::StringHash(const StringHash& other) : m_Hash(other.m_Hash) {
}

StringHash& StringHash::operator=(const StringHash& other) {
    if (this != &other) {
        m_Hash = other.m_Hash;
    }
    return *this;
}

bool StringHash::operator==(const StringHash& other) const {
    return m_Hash == other.m_Hash;
}

bool StringHash::operator!=(const StringHash& other) const {
    return !(*this == other);
}

bool StringHash::operator<(const StringHash& other) const {
    return m_Hash < other.m_Hash;
}

uint32 StringHash::GetHash() const {
    return m_Hash;
}

bool StringHash::IsValid() const {
    return m_Hash != 0;
}

uint32 StringHash::CalculateFNV1a(const char* str) {
    if (str == nullptr) return 0;

    uint32 hash = 2166136261u;
    int32 i = 0;
    while (str[i] != '\0') {
        hash ^= static_cast<uint32>(str[i]);
        hash *= 16777619u;
        ++i;
    }
    return hash;
}

uint32 StringHash::CalculateFNV1a(const char* str, int32 length) {
    if (str == nullptr || length <= 0) return 0;

    uint32 hash = 2166136261u;
    for (int32 i = 0; i < length; ++i) {
        hash ^= static_cast<uint32>(str[i]);
        hash *= 16777619u;
    }
    return hash;
}

}
