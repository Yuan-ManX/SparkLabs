#ifndef SPARKLABS_CORE_OBJECT_OBJECT_H
#define SPARKLABS_CORE_OBJECT_OBJECT_H

#include "Types.h"
#include "memory/SmartPtr.h"
#include "string/String.h"

namespace SparkLabs {

class TypeInfo {
public:
    TypeInfo(const char* name, const TypeInfo* baseType);

    const char* GetName() const;
    const TypeInfo* GetBaseType() const;
    bool IsExactly(const TypeInfo& other) const;
    bool IsDerivedFrom(const TypeInfo& other) const;

private:
    const char* m_Name;
    const TypeInfo* m_BaseType;
};

#define DECLARE_RTTI \
public: \
    static const TypeInfo Type; \
    static const TypeInfo* StaticType(); \
    virtual const TypeInfo* GetType() const; \
    template<typename T> \
    bool IsA() const; \
    template<typename T> \
    T* Cast(); \
    template<typename T> \
    const T* Cast() const;

#define IMPLEMENT_RTTI(className) \
    const TypeInfo className::Type(#className, nullptr); \
    const TypeInfo* className::StaticType() { return &Type; } \
    const TypeInfo* className::GetType() const { return &Type; } \
    template<typename T> \
    bool className::IsA() const { \
        const TypeInfo* myType = GetType(); \
        const TypeInfo* targetType = T::StaticType(); \
        while (myType != nullptr) { \
            if (myType == targetType) return true; \
            myType = myType->GetBaseType(); \
        } \
        return false; \
    } \
    template<typename T> \
    T* className::Cast() { \
        if (IsA<T>()) return static_cast<T*>(this); \
        return nullptr; \
    } \
    template<typename T> \
    const T* className::Cast() const { \
        if (IsA<T>()) return static_cast<const T*>(this); \
        return nullptr; \
    }

class Object {
    DECLARE_RTTI

public:
    Object();
    Object(const Object&) = delete;
    Object& operator=(const Object&) = delete;
    virtual ~Object();

    void AddRef();
    void Release();
    int32 GetRefCount() const;

    bool IsValid() const;
    void Destroy();

protected:
    int32 m_RefCount;
};

}

#endif
