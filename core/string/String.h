#ifndef SPARKAI_CORE_STRING_STRING_H
#define SPARKAI_CORE_STRING_STRING_H

#include "Types.h"
#include <cstddef>

namespace SparkLabs {

class String {
public:
    String();
    String(const char* str);
    String(const char* str, int32 length);
    String(const String& other);
    String(String&& other) noexcept;
    ~String();

    String& operator=(const String& other);
    String& operator=(String&& other) noexcept;
    String& operator=(const char* str);

    String operator+(const String& other) const;
    String operator+(const char* str) const;
    friend String operator+(const char* lhs, const String& rhs);

    String& operator+=(const String& other);
    String& operator+=(const char* str);

    bool operator==(const String& other) const;
    bool operator==(const char* str) const;
    bool operator!=(const String& other) const;
    bool operator!=(const char* str) const;
    bool operator<(const String& other) const;

    char operator[](int32 index) const;
    char& operator[](int32 index);

    int32 Length() const;
    bool Empty() const;
    const char* C_str() const;
    void Clear();

    String Substring(int32 start, int32 length = -1) const;
    int32 Find(const String& substr, int32 startPos = 0) const;
    int32 Find(const char* substr, int32 startPos = 0) const;
    String Replace(const String& search, const String& replace) const;
    String Replace(const char* search, const char* replace) const;

    void Reserve(int32 capacity);
    int32 Capacity() const;

private:
    char* m_Data;
    int32 m_Length;
    int32 m_Capacity;

    void Allocate(int32 capacity);
    void Deallocate();
    void CopyFrom(const char* str, int32 length);
};

}

#endif
