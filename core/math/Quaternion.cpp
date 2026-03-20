#include "math/Quaternion.h"
#include <cmath>

namespace SparkLabs {

const Quaternion Quaternion::IdentityQuaternion(0.0f, 0.0f, 0.0f, 1.0f);

Quaternion::Quaternion() : x(0.0f), y(0.0f), z(0.0f), w(1.0f) {
}

Quaternion::Quaternion(float32 x, float32 y, float32 z, float32 w) : x(x), y(y), z(z), w(w) {
}

Quaternion::Quaternion(const Vector3& eulerDegrees) {
    *this = FromEuler(eulerDegrees);
}

Quaternion::Quaternion(const Quaternion& other) : x(other.x), y(other.y), z(other.z), w(other.w) {
}

Quaternion& Quaternion::operator=(const Quaternion& other) {
    if (this != &other) {
        x = other.x;
        y = other.y;
        z = other.z;
        w = other.w;
    }
    return *this;
}

Quaternion Quaternion::operator+(const Quaternion& other) const {
    return Quaternion(x + other.x, y + other.y, z + other.z, w + other.w);
}

Quaternion Quaternion::operator-(const Quaternion& other) const {
    return Quaternion(x - other.x, y - other.y, z - other.z, w - other.w);
}

Quaternion Quaternion::operator*(const Quaternion& other) const {
    return Multiply(*this, other);
}

Quaternion Quaternion::operator*(float32 scalar) const {
    return Quaternion(x * scalar, y * scalar, z * scalar, w * scalar);
}

Quaternion Quaternion::operator/(float32 scalar) const {
    return Quaternion(x / scalar, y / scalar, z / scalar, w / scalar);
}

Quaternion& Quaternion::operator+=(const Quaternion& other) {
    x += other.x;
    y += other.y;
    z += other.z;
    w += other.w;
    return *this;
}

Quaternion& Quaternion::operator-=(const Quaternion& other) {
    x -= other.x;
    y -= other.y;
    z -= other.z;
    w -= other.w;
    return *this;
}

Quaternion& Quaternion::operator*=(const Quaternion& other) {
    *this = Multiply(*this, other);
    return *this;
}

Quaternion& Quaternion::operator*=(float32 scalar) {
    x *= scalar;
    y *= scalar;
    z *= scalar;
    w *= scalar;
    return *this;
}

Quaternion& Quaternion::operator/=(float32 scalar) {
    x /= scalar;
    y /= scalar;
    z /= scalar;
    w /= scalar;
    return *this;
}

bool Quaternion::operator==(const Quaternion& other) const {
    return x == other.x && y == other.y && z == other.z && w == other.w;
}

bool Quaternion::operator!=(const Quaternion& other) const {
    return !(*this == other);
}

float32 Quaternion::Dot(const Quaternion& other) const {
    return x * other.x + y * other.y + z * other.z + w * other.w;
}

float32 Quaternion::Length() const {
    return std::sqrt(x * x + y * y + z * z + w * w);
}

float32 Quaternion::LengthSquared() const {
    return x * x + y * y + z * z + w * w;
}

Quaternion Quaternion::Normalize() const {
    float32 len = Length();
    if (len > 0.0f) {
        return Quaternion(x / len, y / len, z / len, w / len);
    }
    return IdentityQuaternion;
}

Quaternion Quaternion::Conjugate() const {
    return Quaternion(-x, -y, -z, w);
}

Quaternion Quaternion::Inverse() const {
    float32 lenSq = LengthSquared();
    if (lenSq > 0.0f) {
        return Conjugate() / lenSq;
    }
    return IdentityQuaternion;
}

Vector3 Quaternion::ToEuler() const {
    Vector3 euler;

    float32 sinr_cosp = 2.0f * (w * x + y * z);
    float32 cosr_cosp = 1.0f - 2.0f * (x * x + y * y);
    euler.x = std::atan2(sinr_cosp, cosr_cosp);

    float32 sinp = 2.0f * (w * y - z * x);
    if (std::abs(sinp) >= 1.0f) {
        euler.y = std::copysign(3.14159265359f / 2.0f, sinp);
    } else {
        euler.y = std::asin(sinp);
    }

    float32 siny_cosp = 2.0f * (w * z + x * y);
    float32 cosy_cosp = 1.0f - 2.0f * (y * y + z * z);
    euler.z = std::atan2(siny_cosp, cosy_cosp);

    return euler;
}

Matrix4x4 Quaternion::ToMatrix() const {
    Matrix4x4 result;

    float32 xx = x * x;
    float32 yy = y * y;
    float32 zz = z * z;
    float32 xy = x * y;
    float32 xz = x * z;
    float32 yz = y * z;
    float32 wx = w * x;
    float32 wy = w * y;
    float32 wz = w * z;

    result.m[0] = 1.0f - 2.0f * (yy + zz);
    result.m[1] = 2.0f * (xy + wz);
    result.m[2] = 2.0f * (xz - wy);
    result.m[4] = 2.0f * (xy - wz);
    result.m[5] = 1.0f - 2.0f * (xx + zz);
    result.m[6] = 2.0f * (yz + wx);
    result.m[8] = 2.0f * (xz + wy);
    result.m[9] = 2.0f * (yz - wx);
    result.m[10] = 1.0f - 2.0f * (xx + yy);

    return result;
}

Quaternion Quaternion::FromEuler(const Vector3& eulerDegrees) {
    Vector3 euler = eulerDegrees * (3.14159265359f / 180.0f);

    float32 sinX = std::sin(euler.x * 0.5f);
    float32 cosX = std::cos(euler.x * 0.5f);
    float32 sinY = std::sin(euler.y * 0.5f);
    float32 cosY = std::cos(euler.y * 0.5f);
    float32 sinZ = std::sin(euler.z * 0.5f);
    float32 cosZ = std::cos(euler.z * 0.5f);

    Quaternion result;
    result.w = cosX * cosY * cosZ + sinX * sinY * sinZ;
    result.x = sinX * cosY * cosZ - cosX * sinY * sinZ;
    result.y = cosX * sinY * cosZ + sinX * cosY * sinZ;
    result.z = cosX * cosY * sinZ - sinX * sinY * cosZ;

    return result;
}

Quaternion Quaternion::Slerp(const Quaternion& a, const Quaternion& b, float32 t) {
    float32 cosHalfTheta = a.Dot(b);

    if (std::abs(cosHalfTheta) >= 1.0f) {
        return a;
    }

    float32 halfTheta = std::acos(cosHalfTheta);
    float32 sinHalfTheta = std::sqrt(1.0f - cosHalfTheta * cosHalfTheta);

    if (std::abs(sinHalfTheta) < 0.001f) {
        return Quaternion(
            (a.x + b.x) * 0.5f,
            (a.y + b.y) * 0.5f,
            (a.z + b.z) * 0.5f,
            (a.w + b.w) * 0.5f
        );
    }

    float32 ratioA = std::sin((1.0f - t) * halfTheta) / sinHalfTheta;
    float32 ratioB = std::sin(t * halfTheta) / sinHalfTheta;

    return Quaternion(
        a.x * ratioA + b.x * ratioB,
        a.y * ratioA + b.y * ratioB,
        a.z * ratioA + b.z * ratioB,
        a.w * ratioA + b.w * ratioB
    );
}

Quaternion Quaternion::Multiply(const Quaternion& a, const Quaternion& b) {
    Quaternion result;
    result.w = a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z;
    result.x = a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y;
    result.y = a.w * b.y + a.y * b.w + a.z * b.x - a.x * b.z;
    result.z = a.w * b.z + a.z * b.w + a.x * b.y - a.y * b.x;
    return result;
}

Quaternion Quaternion::Identity() {
    return IdentityQuaternion;
}

}
