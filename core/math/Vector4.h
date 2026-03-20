#ifndef SPARKLABS_CORE_MATH_VECTOR4_H
#define SPARKLABS_CORE_MATH_VECTOR4_H

#include "../Types.h"
#include <cmath>

namespace SparkLabs {

class Vector4 {
public:
    float32 x, y, z, w;

    Vector4() : x(0.0f), y(0.0f), z(0.0f), w(0.0f) {}
    Vector4(float32 x_, float32 y_, float32 z_, float32 w_) : x(x_), y(y_), z(z_), w(w_) {}

    static Vector4 Zero() { return Vector4(0.0f, 0.0f, 0.0f, 0.0f); }
    static Vector4 One() { return Vector4(1.0f, 1.0f, 1.0f, 1.0f); }

    float32 Dot(const Vector4& other) const { return x * other.x + y * other.y + z * other.z + w * other.w; }
    float32 LengthSquared() const { return x * x + y * y + z * z + w * w; }
    float32 Length() const { return sqrtf(LengthSquared()); }

    Vector4 Normalized() const {
        float32 len = Length();
        if (len > 0.0f) {
            return *this / len;
        }
        return Zero();
    }
};

}

#endif
