#include "AIBlackboard.h"

namespace SparkLabs {

Variant::Variant()
    : m_Type(Type::None)
    , int32Value(0) {
}

Variant::Variant(int32 value)
    : m_Type(Type::Int32)
    , int32Value(value) {
}

Variant::Variant(float32 value)
    : m_Type(Type::Float32)
    , float32Value(value) {
}

Variant::Variant(float64 value)
    : m_Type(Type::Float64)
    , float64Value(value) {
}

Variant::Variant(const String& value)
    : m_Type(Type::String)
    , stringValue(value) {
}

Variant::Variant(const char* value)
    : m_Type(Type::String)
    , stringValue(value) {
}

Variant::Variant(bool value)
    : m_Type(Type::Bool)
    , boolValue(value) {
}

Variant::Variant(const Variant& other)
    : m_Type(other.m_Type)
    , int32Value(0) {
    switch (m_Type) {
        case Type::Int32:
            int32Value = other.int32Value;
            break;
        case Type::Float32:
            float32Value = other.float32Value;
            break;
        case Type::Float64:
            float64Value = other.float64Value;
            break;
        case Type::String:
            new (&stringValue) String(other.stringValue);
            break;
        case Type::Bool:
            boolValue = other.boolValue;
            break;
        case Type::None:
            break;
    }
}

Variant::Variant(Variant&& other) noexcept
    : m_Type(other.m_Type)
    , int32Value(0) {
    switch (m_Type) {
        case Type::String:
            new (&stringValue) String(std::move(other.stringValue));
            break;
        default:
            int32Value = other.int32Value;
            break;
    }
    other.m_Type = Type::None;
}

Variant::~Variant() {
    if (m_Type == Type::String) {
        stringValue.~String();
    }
}

Variant& Variant::operator=(const Variant& other) {
    if (this != &other) {
        if (m_Type == Type::String) {
            stringValue.~String();
        }
        m_Type = other.m_Type;
        switch (m_Type) {
            case Type::Int32:
                int32Value = other.int32Value;
                break;
            case Type::Float32:
                float32Value = other.float32Value;
                break;
            case Type::Float64:
                float64Value = other.float64Value;
                break;
            case Type::String:
                new (&stringValue) String(other.stringValue);
                break;
            case Type::Bool:
                boolValue = other.boolValue;
                break;
            case Type::None:
                break;
        }
    }
    return *this;
}

Variant& Variant::operator=(Variant&& other) noexcept {
    if (this != &other) {
        if (m_Type == Type::String) {
            stringValue.~String();
        }
        m_Type = other.m_Type;
        switch (m_Type) {
            case Type::String:
                new (&stringValue) String(std::move(other.stringValue));
                break;
            default:
                int32Value = other.int32Value;
                break;
        }
        other.m_Type = Type::None;
    }
    return *this;
}

bool Variant::operator==(const Variant& other) const {
    if (m_Type != other.m_Type) return false;
    switch (m_Type) {
        case Type::Int32:
            return int32Value == other.int32Value;
        case Type::Float32:
            return float32Value == other.float32Value;
        case Type::Float64:
            return float64Value == other.float64Value;
        case Type::String:
            return stringValue == other.stringValue;
        case Type::Bool:
            return boolValue == other.boolValue;
        case Type::None:
            return true;
    }
    return false;
}

bool Variant::operator!=(const Variant& other) const {
    return !(*this == other);
}

int32 Variant::GetInt32() const {
    switch (m_Type) {
        case Type::Int32:
            return int32Value;
        case Type::Float32:
            return static_cast<int32>(float32Value);
        case Type::Float64:
            return static_cast<int32>(float64Value);
        case Type::Bool:
            return boolValue ? 1 : 0;
        default:
            return 0;
    }
}

float32 Variant::GetFloat32() const {
    switch (m_Type) {
        case Type::Int32:
            return static_cast<float32>(int32Value);
        case Type::Float32:
            return float32Value;
        case Type::Float64:
            return static_cast<float32>(float64Value);
        case Type::Bool:
            return boolValue ? 1.0f : 0.0f;
        default:
            return 0.0f;
    }
}

float64 Variant::GetFloat64() const {
    switch (m_Type) {
        case Type::Int32:
            return static_cast<float64>(int32Value);
        case Type::Float32:
            return static_cast<float64>(float32Value);
        case Type::Float64:
            return float64Value;
        case Type::Bool:
            return boolValue ? 1.0 : 0.0;
        default:
            return 0.0;
    }
}

const String& Variant::GetString() const {
    static String empty;
    if (m_Type == Type::String) {
        return stringValue;
    }
    return empty;
}

bool Variant::GetBool() const {
    switch (m_Type) {
        case Type::Bool:
            return boolValue;
        case Type::Int32:
            return int32Value != 0;
        case Type::Float32:
            return float32Value != 0.0f;
        case Type::Float64:
            return float64Value != 0.0;
        default:
            return false;
    }
}

AIBlackboard::AIBlackboard()
    : m_CurrentTimestamp(0.0) {
}

AIBlackboard::~AIBlackboard() {
    m_Entries.clear();
}

Variant AIBlackboard::Get(const String& key, const Variant& defaultValue) const {
    StringHash hash(key);
    auto it = m_Entries.find(hash);
    if (it != m_Entries.end()) {
        return it->second.value;
    }
    return defaultValue;
}

bool AIBlackboard::Has(const String& key) const {
    StringHash hash(key);
    return m_Entries.find(hash) != m_Entries.end();
}

void AIBlackboard::Clear() {
    m_Entries.clear();
}

void AIBlackboard::Share(const String& key) {
    StringHash hash(key);
    auto it = m_Entries.find(hash);
    if (it != m_Entries.end()) {
        it->second.isShared = true;
    }
}

void AIBlackboard::Unshare(const String& key) {
    StringHash hash(key);
    auto it = m_Entries.find(hash);
    if (it != m_Entries.end()) {
        it->second.isShared = false;
    }
}

void AIBlackboard::SetTimestamp(float64 timestamp) {
    m_CurrentTimestamp = timestamp;
}

float64 AIBlackboard::GetCurrentTimestamp() const {
    return m_CurrentTimestamp;
}

}