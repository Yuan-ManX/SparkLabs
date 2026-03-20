#include "math/Vector3.h"
#include <cmath>

namespace SparkLabs {

const Vector3 Vector3::Zero(0.0f, 0.0f, 0.0f);
const Vector3 Vector3::One(1.0f, 1.0f, 1.0f);
const Vector3 Vector3::UnitX(1.0f, 0.0f, 0.0f);
const Vector3 Vector3::UnitY(0.0f, 1.0f, 0.0f);
const Vector3 Vector3::UnitZ(0.0f, 0.0f, 1.0f);

Vector3::Vector3() : x(0.0f), y(0.0f), z(0.0f) {
}

Vector3::Vector3(float32 x, float32 y, float32 z) : x(x), y(y), z(z) {
}

Vector3::Vector3(float32 scalar) : x(scalar), y(scalar), z(scalar) {
}

Vector3::Vector3(const Vector3& other) : x(other.x), y(other.y), z(other.z) {
}

Vector3& Vector3::operator=(const Vector3& other) {
    if (this != &other) {
        x = other.x;
        y = other.y;
        z = other.z;
    }
    return *this;
}

Vector3 Vector3::operator+(const Vector3& other) const {
    return Vector3(x + other.x, y + other.y, z + other.z);
}

Vector3 Vector3::operator-(const Vector3& other) const {
    return Vector3(x - other.x, y - other.y, z - other.z);
}

Vector3 Vector3::operator*(float32 scalar) const {
    return Vector3(x * scalar, y * scalar, z * scalar);
}

Vector3 Vector3::operator/(float32 scalar) const {
    return Vector3(x / scalar, y / scalar, z / scalar);
}

Vector3& Vector3::operator+=(const Vector3& other) {
    x += other.x;
    y += other.y;
    z += other.z;
    return *this;
}

Vector3& Vector3::operator-=(const Vector3& other) {
    x -= other.x;
    y -= other.y;
    z -= other.z;
    return *this;
}

Vector3& Vector3::operator*=(float32 scalar) {
    x *= scalar;
    y *= scalar;
    z *= scalar;
    return *this;
}

Vector3& Vector3::operator/=(float32 scalar) {
    x /= scalar;
    y /= scalar;
    z /= scalar;
    return *this;
}

bool Vector3::operator==(const Vector3& other) const {
    return x == other.x && y == other.y && z == other.z;
}

bool Vector3::operator!=(const Vector3& other) const {
    return !(*this == other);
}

float32 Vector3::Dot(const Vector3& other) const {
    return x * other.x + y * other.y + z * other.z;
}

Vector3 Vector3::Cross(const Vector3& other) const {
    return Vector3(
        y * other.z - z * other.y,
        z * other.x - x * other.z,
        x * other.y - y * other.x
    );
}

float32 Vector3::Length() const {
    return std::sqrt(x * x + y * y + z * z);
}

float32 Vector3::LengthSquared() const {
    return x * x + y * y + z * z;
}

Vector3 Vector3::Normalize() const {
    float32 len = Length();
    if (len > 0.0f) {
        return Vector3(x / len, y / len, z / len);
    }
    return Vector3::Zero;
}

Vector3 Vector3::Lerp(const Vector3& other, float32 t) const {
    return Vector3(x + (other.x - x) * t, y + (other.y - y) * t, z + (other.z - z) * t);
}

}
