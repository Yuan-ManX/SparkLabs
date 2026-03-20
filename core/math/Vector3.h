#ifndef SPARKLABS_CORE_MATH_VECTOR3_H
#define SPARKLABS_CORE_MATH_VECTOR3_H

#include "../Types.h"
#include <cmath>

namespace SparkLabs {

class Vector3 {
public:
    float32 x, y, z;

    Vector3() : x(0.0f), y(0.0f), z(0.0f) {}
    Vector3(float32 x_, float32 y_, float32 z_) : x(x_), y(y_), z(z_) {}

    static Vector3 Zero() { return Vector3(0.0f, 0.0f, 0.0f); }
    static Vector3 One() { return Vector3(1.0f, 1.0f, 1.0f); }
    static Vector3 Up() { return Vector3(0.0f, 1.0f, 0.0f); }
    static Vector3 Down() { return Vector3(0.0f, -1.0f, 0.0f); }
    static Vector3 Right() { return Vector3(1.0f, 0.0f, 0.0f); }
    static Vector3 Left() { return Vector3(-1.0f, 0.0f, 0.0f); }
    static Vector3 Forward() { return Vector3(0.0f, 0.0f, 1.0f); }

    Vector3 operator+(const Vector3& other) const { return Vector3(x + other.x, y + other.y, z + other.z); }
    Vector3 operator-(const Vector3& other) const { return Vector3(x - other.x, y - other.y, z - other.z); }
    Vector3 operator*(float32 scalar) const { return Vector3(x * scalar, y * scalar, z * scalar); }
    Vector3 operator/(float32 scalar) const { return Vector3(x / scalar, y / scalar, z / scalar); }

    Vector3& operator+=(const Vector3& other) { x += other.x; y += other.y; z += other.z; return *this; }
    Vector3& operator-=(const Vector3& other) { x -= other.x; y -= other.y; z -= other.z; return *this; }
    Vector3& operator*=(float32 scalar) { x *= scalar; y *= scalar; z *= scalar; return *this; }
    Vector3& operator/=(float32 scalar) { x /= scalar; y /= scalar; z /= scalar; return *this; }

    Vector3 operator-() const { return Vector3(-x, -y, -z); }

    bool operator==(const Vector3& other) const { return x == other.x && y == other.y && z == other.z; }
    bool operator!=(const Vector3& other) const { return !(*this == other); }

    float32 Dot(const Vector3& other) const { return x * other.x + y * other.y + z * other.z; }
    Vector3 Cross(const Vector3& other) const {
        return Vector3(
            y * other.z - z * other.y,
            z * other.x - x * other.z,
            x * other.y - y * other.x
        );
    }

    float32 LengthSquared() const { return x * x + y * y + z * z; }
    float32 Length() const { return sqrtf(LengthSquared()); }

    Vector3 Normalized() const {
        float32 len = Length();
        if (len > 0.0f) {
            return *this / len;
        }
        return Zero();
    }

    void Normalize() {
        float32 len = Length();
        if (len > 0.0f) {
            x /= len;
            y /= len;
            z /= len;
        }
    }

    static float32 Distance(const Vector3& a, const Vector3& b) { return (a - b).Length(); }
    static float32 DistanceSquared(const Vector3& a, const Vector3& b) { return (a - b).LengthSquared(); }

    static Vector3 Lerp(const Vector3& a, const Vector3& b, float32 t) {
        return a + (b - a) * t;
    }

    static Vector3 Clamp(const Vector3& value, const Vector3& min, const Vector3& max) {
        return Vector3(
            value.x < min.x ? min.x : (value.x > max.x ? max.x : value.x),
            value.y < min.y ? min.y : (value.y > max.y ? max.y : value.y),
            value.z < min.z ? min.z : (value.z > max.z ? max.z : value.z)
        );
    }

    static Vector3 Project(const Vector3& vector, const Vector3& onNormal) {
        float32 sqrMag = onNormal.Dot(onNormal);
        if (sqrMag < 1e-6f) return Zero();
        return onNormal * (vector.Dot(onNormal) / sqrMag);
    }
};

inline Vector3 operator*(float32 scalar, const Vector3& v) { return v * scalar; }

}

#endif
