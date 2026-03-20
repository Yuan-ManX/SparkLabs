#ifndef SPARKAI_AI_BRAIN_AIBLACKBOARD_H
#define SPARKAI_AI_BRAIN_AIBLACKBOARD_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/string/StringHash.h"
#include "../../core/io/Vector.h"
#include <map>

namespace SparkLabs {

class Variant {
public:
    Variant();
    Variant(int32 value);
    Variant(float32 value);
    Variant(float64 value);
    Variant(const String& value);
    Variant(const char* value);
    Variant(bool value);
    Variant(const Variant& other);
    Variant(Variant&& other) noexcept;
    ~Variant();

    Variant& operator=(const Variant& other);
    Variant& operator=(Variant&& other) noexcept;

    bool operator==(const Variant& other) const;
    bool operator!=(const Variant& other) const;

    enum class Type {
        None,
        Int32,
        Float32,
        Float64,
        String,
        Bool
    };

    Type GetType() const { return m_Type; }
    bool IsValid() const { return m_Type != Type::None; }

    int32 GetInt32() const;
    float32 GetFloat32() const;
    float64 GetFloat64() const;
    const String& GetString() const;
    bool GetBool() const;

    template<typename T>
    T Get() const;

private:
    Type m_Type;
    union {
        int32 int32Value;
        float32 float32Value;
        float64 float64Value;
        bool boolValue;
    };
    String stringValue;
};

struct AIBlackboardEntry {
    Variant value;
    bool isShared;
    float64 timestamp;

    AIBlackboardEntry()
        : isShared(false)
        , timestamp(0.0) {
    }

    AIBlackboardEntry(const Variant& val, bool shared = false, float64 time = 0.0)
        : value(val)
        , isShared(shared)
        , timestamp(time) {
    }
};

class AIBlackboard {
public:
    AIBlackboard();
    ~AIBlackboard();

    template<typename T>
    void Set(const String& key, const T& value);

    Variant Get(const String& key, const Variant& defaultValue = Variant()) const;
    bool Has(const String& key) const;
    void Clear();

    void Share(const String& key);
    void Unshare(const String& key);

    void SetTimestamp(float64 timestamp);
    float64 GetCurrentTimestamp() const;

    using EntryMap = std::map<StringHash, AIBlackboardEntry>;
    const EntryMap& GetAllEntries() const { return m_Entries; }

private:
    EntryMap m_Entries;
    float64 m_CurrentTimestamp;
};

template<typename T>
void AIBlackboard::Set(const String& key, const T& value) {
    StringHash hash(key);
    AIBlackboardEntry entry;
    entry.value = Variant(value);
    entry.isShared = false;
    entry.timestamp = m_CurrentTimestamp;
    m_Entries[hash] = entry;
}

template<>
inline int32 Variant::Get<int32>() const {
    return GetInt32();
}

template<>
inline float32 Variant::Get<float32>() const {
    return GetFloat32();
}

template<>
inline float64 Variant::Get<float64>() const {
    return GetFloat64();
}

template<>
inline String Variant::Get<String>() const {
    return GetString();
}

template<>
inline bool Variant::Get<bool>() const {
    return GetBool();
}

}

#endif