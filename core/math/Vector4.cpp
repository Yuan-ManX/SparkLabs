#include "math/Vector4.h"
#include <cmath>

namespace SparkLabs {

const Vector4 Vector4::Zero(0.0f, 0.0f, 0.0f, 0.0f);
const Vector4 Vector4::One(1.0f, 1.0f, 1.0f, 1.0f);

Vector4::Vector4() : x(0.0f), y(0.0f), z(0.0f), w(0.0f) {
}

Vector4::Vector4(float32 x, float32 y, float32 z, float32 w) : x(x), y(y), z(z), w(w) {
}

Vector4::Vector4(float32 scalar) : x(scalar), y(scalar), z(scalar), w(scalar) {
}

Vector4::Vector4(const Vector4& other) : x(other.x), y(other.y), z(other.z), w(other.w) {
}

Vector4& Vector4::operator=(const Vector4& other) {
    if (this != &other) {
        x = other.x;
        y = other.y;
        z = other.z;
        w = other.w;
    }
    return *this;
}

Vector4 Vector4::operator+(const Vector4& other) const {
    return Vector4(x + other.x, y + other.y, z + other.z, w + other.w);
}

Vector4 Vector4::operator-(const Vector4& other) const {
    return Vector4(x - other.x, y - other.y, z - other.z, w - other.w);
}

Vector4 Vector4::operator*(float32 scalar) const {
    return Vector4(x * scalar, y * scalar, z * scalar, w * scalar);
}

Vector4 Vector4::operator/(float32 scalar) const {
    return Vector4(x / scalar, y / scalar, z / scalar, w / scalar);
}

Vector4& Vector4::operator+=(const Vector4& other) {
    x += other.x;
    y += other.y;
    z += other.z;
    w += other.w;
    return *this;
}

Vector4& Vector4::operator-=(const Vector4& other) {
    x -= other.x;
    y -= other.y;
    z -= other.z;
    w -= other.w;
    return *this;
}

Vector4& Vector4::operator*=(float32 scalar) {
    x *= scalar;
    y *= scalar;
    z *= scalar;
    w *= scalar;
    return *this;
}

Vector4& Vector4::operator/=(float32 scalar) {
    x /= scalar;
    y /= scalar;
    z /= scalar;
    w /= scalar;
    return *this;
}

bool Vector4::operator==(const Vector4& other) const {
    return x == other.x && y == other.y && z == other.z && w == other.w;
}

bool Vector4::operator!=(const Vector4& other) const {
    return !(*this == other);
}

float32 Vector4::Dot(const Vector4& other) const {
    return x * other.x + y * other.y + z * other.z + w * other.w;
}

float32 Vector4::Length() const {
    return std::sqrt(x * x + y * y + z * z + w * w);
}

float32 Vector4::LengthSquared() const {
    return x * x + y * y + z * z + w * w;
}

Vector4 Vector4::Normalize() const {
    float32 len = Length();
    if (len > 0.0f) {
        return Vector4(x / len, y / len, z / len, w / len);
    }
    return Vector4::Zero;
}

Vector4 Vector4::Lerp(const Vector4& other, float32 t) const {
    return Vector4(x + (other.x - x) * t, y + (other.y - y) * t, z + (other.z - z) * t, w + (other.w - w) * t);
}

}
