#include "math/Vector2.h"
#include <cmath>

namespace SparkLabs {

const Vector2 Vector2::Zero(0.0f, 0.0f);
const Vector2 Vector2::One(1.0f, 1.0f);
const Vector2 Vector2::UnitX(1.0f, 0.0f);
const Vector2 Vector2::UnitY(0.0f, 1.0f);

Vector2::Vector2() : x(0.0f), y(0.0f) {
}

Vector2::Vector2(float32 x, float32 y) : x(x), y(y) {
}

Vector2::Vector2(float32 scalar) : x(scalar), y(scalar) {
}

Vector2::Vector2(const Vector2& other) : x(other.x), y(other.y) {
}

Vector2& Vector2::operator=(const Vector2& other) {
    if (this != &other) {
        x = other.x;
        y = other.y;
    }
    return *this;
}

Vector2 Vector2::operator+(const Vector2& other) const {
    return Vector2(x + other.x, y + other.y);
}

Vector2 Vector2::operator-(const Vector2& other) const {
    return Vector2(x - other.x, y - other.y);
}

Vector2 Vector2::operator*(float32 scalar) const {
    return Vector2(x * scalar, y * scalar);
}

Vector2 Vector2::operator/(float32 scalar) const {
    return Vector2(x / scalar, y / scalar);
}

Vector2& Vector2::operator+=(const Vector2& other) {
    x += other.x;
    y += other.y;
    return *this;
}

Vector2& Vector2::operator-=(const Vector2& other) {
    x -= other.x;
    y -= other.y;
    return *this;
}

Vector2& Vector2::operator*=(float32 scalar) {
    x *= scalar;
    y *= scalar;
    return *this;
}

Vector2& Vector2::operator/=(float32 scalar) {
    x /= scalar;
    y /= scalar;
    return *this;
}

bool Vector2::operator==(const Vector2& other) const {
    return x == other.x && y == other.y;
}

bool Vector2::operator!=(const Vector2& other) const {
    return !(*this == other);
}

float32 Vector2::Dot(const Vector2& other) const {
    return x * other.x + y * other.y;
}

float32 Vector2::Cross(const Vector2& other) const {
    return x * other.y - y * other.x;
}

float32 Vector2::Length() const {
    return std::sqrt(x * x + y * y);
}

float32 Vector2::LengthSquared() const {
    return x * x + y * y;
}

Vector2 Vector2::Normalize() const {
    float32 len = Length();
    if (len > 0.0f) {
        return Vector2(x / len, y / len);
    }
    return Vector2::Zero;
}

Vector2 Vector2::Lerp(const Vector2& other, float32 t) const {
    return Vector2(x + (other.x - x) * t, y + (other.y - y) * t);
}

}
