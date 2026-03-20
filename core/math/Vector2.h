#ifndef SPARKLABS_CORE_MATH_VECTOR2_H
#define SPARKLABS_CORE_MATH_VECTOR2_H

#include "../Types.h"
#include <cmath>

namespace SparkLabs {

class Vector2 {
public:
    float32 x, y;

    Vector2() : x(0.0f), y(0.0f) {}
    Vector2(float32 x_, float32 y_) : x(x_), y(y_) {}

    static Vector2 Zero() { return Vector2(0.0f, 0.0f); }
    static Vector2 One() { return Vector2(1.0f, 1.0f); }

    Vector2 operator+(const Vector2& other) const { return Vector2(x + other.x, y + other.y); }
    Vector2 operator-(const Vector2& other) const { return Vector2(x - other.x, y - other.y); }
    Vector2 operator*(float32 scalar) const { return Vector2(x * scalar, y * scalar); }
    Vector2 operator/(float32 scalar) const { return Vector2(x / scalar, y / scalar); }

    float32 Dot(const Vector2& other) const { return x * other.x + y * other.y; }
    float32 Cross(const Vector2& other) const { return x * other.y - y * other.x; }

    float32 LengthSquared() const { return x * x + y * y; }
    float32 Length() const { return sqrtf(LengthSquared()); }

    Vector2 Normalized() const {
        float32 len = Length();
        if (len > 0.0f) {
            return *this / len;
        }
        return Zero();
    }

    static Vector2 Lerp(const Vector2& a, const Vector2& b, float32 t) {
        return a + (b - a) * t;
    }
};

inline Vector2 operator*(float32 scalar, const Vector2& v) { return v * scalar; }

}

#endif
