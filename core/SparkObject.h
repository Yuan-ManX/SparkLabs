#ifndef SPARKLABS_SPARKOBJECT_H
#define SPARKLABS_SPARKOBJECT_H

#define SPARKLABS_OBJECT(ClassName) \
    public: \
        static const SparkLabs::StringHash& GetTypeStatic() { \
            static SparkLabs::StringHash type(#ClassName); \
            return type; \
        } \
        virtual const SparkLabs::StringHash& GetType() const override { \
            return GetTypeStatic(); \
        } \
        virtual bool IsA(const SparkLabs::StringHash& type) const override { \
            return type == GetTypeStatic() || SparkLabs::Object::IsA(type); \
        }

#define SPARKLABS_CLASS(ClassName) \
    SPARKLABS_OBJECT(ClassName) \
    public:

#endif
