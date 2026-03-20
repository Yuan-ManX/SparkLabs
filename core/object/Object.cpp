#include "Object.h"

namespace SparkLabs {

TypeInfo::TypeInfo(const char* name, const TypeInfo* baseType)
    : m_Name(name)
    , m_BaseType(baseType)
{
}

const char* TypeInfo::GetName() const {
    return m_Name;
}

const TypeInfo* TypeInfo::GetBaseType() const {
    return m_BaseType;
}

bool TypeInfo::IsExactly(const TypeInfo& other) const {
    return m_Name == other.m_Name;
}

bool TypeInfo::IsDerivedFrom(const TypeInfo& other) const {
    const TypeInfo* current = this;
    while (current != nullptr) {
        if (current->IsExactly(other)) {
            return true;
        }
        current = current->GetBaseType();
    }
    return false;
}

Object::Object()
    : m_RefCount(0)
{
}

Object::~Object() {
}

void Object::AddRef() {
    ++m_RefCount;
}

void Object::Release() {
    --m_RefCount;
    if (m_RefCount <= 0) {
        delete this;
    }
}

int32 Object::GetRefCount() const {
    return m_RefCount;
}

bool Object::IsValid() const {
    return m_RefCount > 0;
}

void Object::Destroy() {
    Release();
}

}
