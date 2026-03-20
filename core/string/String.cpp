#include "string/String.h"
#include <cstring>
#include <algorithm>
#include <stdexcept>

namespace SparkLabs {

String::String() : m_Data(nullptr), m_Length(0), m_Capacity(0) {
}

String::String(const char* str) : m_Data(nullptr), m_Length(0), m_Capacity(0) {
    if (str != nullptr) {
        int32 len = 0;
        while (str[len] != '\0') ++len;
        CopyFrom(str, len);
    }
}

String::String(const char* str, int32 length) : m_Data(nullptr), m_Length(0), m_Capacity(0) {
    if (str != nullptr && length > 0) {
        CopyFrom(str, length);
    }
}

String::String(const String& other) : m_Data(nullptr), m_Length(0), m_Capacity(0) {
    if (other.m_Length > 0) {
        CopyFrom(other.m_Data, other.m_Length);
    }
}

String::String(String&& other) noexcept : m_Data(other.m_Data), m_Length(other.m_Length), m_Capacity(other.m_Capacity) {
    other.m_Data = nullptr;
    other.m_Length = 0;
    other.m_Capacity = 0;
}

String::~String() {
    Deallocate();
}

String& String::operator=(const String& other) {
    if (this != &other) {
        Deallocate();
        if (other.m_Length > 0) {
            CopyFrom(other.m_Data, other.m_Length);
        }
    }
    return *this;
}

String& String::operator=(String&& other) noexcept {
    if (this != &other) {
        Deallocate();
        m_Data = other.m_Data;
        m_Length = other.m_Length;
        m_Capacity = other.m_Capacity;
        other.m_Data = nullptr;
        other.m_Length = 0;
        other.m_Capacity = 0;
    }
    return *this;
}

String& String::operator=(const char* str) {
    Deallocate();
    m_Data = nullptr;
    m_Length = 0;
    m_Capacity = 0;
    if (str != nullptr) {
        int32 len = 0;
        while (str[len] != '\0') ++len;
        CopyFrom(str, len);
    }
    return *this;
}

String String::operator+(const String& other) const {
    String result;
    result.CopyFrom(m_Data, m_Length);
    result.CopyFrom(other.m_Data, other.m_Length);
    return result;
}

String String::operator+(const char* str) const {
    String result;
    result.CopyFrom(m_Data, m_Length);
    if (str != nullptr) {
        int32 len = 0;
        while (str[len] != '\0') ++len;
        result.CopyFrom(str, len);
    }
    return result;
}

String operator+(const char* lhs, const String& rhs) {
    String result;
    if (lhs != nullptr) {
        int32 len = 0;
        while (lhs[len] != '\0') ++len;
        result.CopyFrom(lhs, len);
    }
    result.CopyFrom(rhs.m_Data, rhs.m_Length);
    return result;
}

String& String::operator+=(const String& other) {
    int32 oldLength = m_Length;
    Reserve(m_Length + other.m_Length);
    CopyFrom(other.m_Data, other.m_Length);
    return *this;
}

String& String::operator+=(const char* str) {
    if (str != nullptr) {
        int32 len = 0;
        while (str[len] != '\0') ++len;
        int32 oldLength = m_Length;
        Reserve(m_Length + len);
        CopyFrom(str, len);
    }
    return *this;
}

bool String::operator==(const String& other) const {
    if (m_Length != other.m_Length) return false;
    if (m_Data == other.m_Data) return true;
    if (m_Data == nullptr || other.m_Data == nullptr) return false;
    return std::strcmp(m_Data, other.m_Data) == 0;
}

bool String::operator==(const char* str) const {
    if (str == nullptr) return m_Length == 0;
    if (m_Data == nullptr) return str[0] == '\0';
    return std::strcmp(m_Data, str) == 0;
}

bool String::operator!=(const String& other) const {
    return !(*this == other);
}

bool String::operator!=(const char* str) const {
    return !(*this == str);
}

bool String::operator<(const String& other) const {
    if (m_Data == nullptr && other.m_Data == nullptr) return false;
    if (m_Data == nullptr) return true;
    if (other.m_Data == nullptr) return false;
    return std::strcmp(m_Data, other.m_Data) < 0;
}

char String::operator[](int32 index) const {
    if (index < 0 || index >= m_Length) return '\0';
    return m_Data[index];
}

char& String::operator[](int32 index) {
    static char nullChar = '\0';
    if (index < 0 || index >= m_Length) return nullChar;
    return m_Data[index];
}

int32 String::Length() const {
    return m_Length;
}

bool String::Empty() const {
    return m_Length == 0;
}

const char* String::C_str() const {
    return m_Data ? m_Data : "";
}

void String::Clear() {
    if (m_Data != nullptr && m_Length > 0) {
        m_Data[0] = '\0';
    }
    m_Length = 0;
}

String String::Substring(int32 start, int32 length) const {
    if (start < 0) start = 0;
    if (start >= m_Length) return String();
    if (length < 0 || start + length > m_Length) {
        length = m_Length - start;
    }
    return String(m_Data + start, length);
}

int32 String::Find(const String& substr, int32 startPos) const {
    return Find(substr.m_Data, startPos);
}

int32 String::Find(const char* substr, int32 startPos) const {
    if (substr == nullptr || m_Data == nullptr) return -1;
    if (startPos < 0) startPos = 0;
    if (startPos >= m_Length) return -1;

    int32 subLen = 0;
    while (substr[subLen] != '\0') ++subLen;
    if (subLen == 0) return startPos;

    for (int32 i = startPos; i <= m_Length - subLen; ++i) {
        bool match = true;
        for (int32 j = 0; j < subLen; ++j) {
            if (m_Data[i + j] != substr[j]) {
                match = false;
                break;
            }
        }
        if (match) return i;
    }
    return -1;
}

String String::Replace(const String& search, const String& replace) const {
    return Replace(search.m_Data, replace.m_Data);
}

String String::Replace(const char* search, const char* replace) const {
    if (search == nullptr || m_Data == nullptr) return *this;

    int32 searchLen = 0;
    while (search[searchLen] != '\0') ++searchLen;
    if (searchLen == 0) return *this;

    int32 replaceLen = 0;
    if (replace != nullptr) {
        while (replace[replaceLen] != '\0') ++replaceLen;
    }

    String result;
    int32 pos = 0;
    while (pos <= m_Length - searchLen) {
        bool match = true;
        for (int32 i = 0; i < searchLen; ++i) {
            if (m_Data[pos + i] != search[i]) {
                match = false;
                break;
            }
        }
        if (match) {
            result.CopyFrom(replace, replaceLen);
            pos += searchLen;
        } else {
            result.CopyFrom(m_Data + pos, 1);
            ++pos;
        }
    }

    while (pos < m_Length) {
        result.CopyFrom(m_Data + pos, 1);
        ++pos;
    }

    return result;
}

void String::Reserve(int32 capacity) {
    if (capacity <= m_Capacity) return;
    Allocate(capacity);
}

int32 String::Capacity() const {
    return m_Capacity;
}

void String::Allocate(int32 capacity) {
    if (capacity <= m_Capacity) return;

    int32 newCapacity = (m_Capacity == 0) ? 16 : m_Capacity * 2;
    while (newCapacity < capacity) {
        newCapacity *= 2;
    }

    char* newData = new char[newCapacity];
    if (m_Data != nullptr) {
        for (int32 i = 0; i < m_Length; ++i) {
            newData[i] = m_Data[i];
        }
        delete[] m_Data;
    }
    newData[m_Length] = '\0';

    m_Data = newData;
    m_Capacity = newCapacity;
}

void String::Deallocate() {
    if (m_Data != nullptr) {
        delete[] m_Data;
        m_Data = nullptr;
    }
    m_Length = 0;
    m_Capacity = 0;
}

void String::CopyFrom(const char* str, int32 length) {
    if (length <= 0) return;

    int32 requiredCapacity = length + 1;
    if (requiredCapacity > m_Capacity) {
        Allocate(requiredCapacity);
    }

    for (int32 i = 0; i < length; ++i) {
        m_Data[i] = str[i];
    }
    m_Data[length] = '\0';
    m_Length = length;
}

}
