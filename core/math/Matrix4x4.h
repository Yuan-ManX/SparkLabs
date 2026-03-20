#ifndef SPARKLABS_CORE_MATH_MATRIX4X4_H
#define SPARKLABS_CORE_MATH_MATRIX4X4_H

#include "../Types.h"
#include "Vector3.h"
#include "Quaternion.h"

namespace SparkLabs {

class Matrix4x4 {
public:
    float32 m[16];

    Matrix4x4() { LoadIdentity(); }

    static Matrix4x4 Identity() {
        Matrix4x4 result;
        result.LoadIdentity();
        return result;
    }

    void LoadIdentity() {
        m[0] = 1; m[1] = 0; m[2] = 0; m[3] = 0;
        m[4] = 0; m[5] = 1; m[6] = 0; m[7] = 0;
        m[8] = 0; m[9] = 0; m[10] = 1; m[11] = 0;
        m[12] = 0; m[13] = 0; m[14] = 0; m[15] = 1;
    }

    Matrix4x4 operator*(const Matrix4x4& other) const {
        Matrix4x4 result;
        for (int row = 0; row < 4; ++row) {
            for (int col = 0; col < 4; ++col) {
                result.m[row * 4 + col] =
                    m[row * 4 + 0] * other.m[0 * 4 + col] +
                    m[row * 4 + 1] * other.m[1 * 4 + col] +
                    m[row * 4 + 2] * other.m[2 * 4 + col] +
                    m[row * 4 + 3] * other.m[3 * 4 + col];
            }
        }
        return result;
    }

    Vector3 operator*(const Vector3& v) const {
        return TransformPoint(v);
    }

    Vector3 TransformPoint(const Vector3& v) const {
        float32 x = m[0] * v.x + m[4] * v.y + m[8] * v.z + m[12];
        float32 y = m[1] * v.x + m[5] * v.y + m[9] * v.z + m[13];
        float32 z = m[2] * v.x + m[6] * v.y + m[10] * v.z + m[14];
        return Vector3(x, y, z);
    }

    Vector3 TransformVector(const Vector3& v) const {
        float32 x = m[0] * v.x + m[4] * v.y + m[8] * v.z;
        float32 y = m[1] * v.x + m[5] * v.y + m[9] * v.z;
        float32 z = m[2] * v.x + m[6] * v.y + m[10] * v.z;
        return Vector3(x, y, z);
    }

    Vector3 TransformDirection(const Vector3& v) const {
        return TransformVector(v.Normalized());
    }

    Matrix4x4 Transpose() const {
        Matrix4x4 result;
        for (int row = 0; row < 4; ++row) {
            for (int col = 0; col < 4; ++col) {
                result.m[row * 4 + col] = m[col * 4 + row];
            }
        }
        return result;
    }

    Matrix4x4 Inverse() const {
        float32 inv[16];
        inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10];
        inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10];
        inv[8] = m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15] + m[8] * m[7] * m[13] + m[12] * m[5] * m[11] - m[12] * m[7] * m[9];
        inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9];
        inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10];
        inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10];
        inv[9] = -m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15] - m[8] * m[3] * m[13] - m[12] * m[1] * m[11] + m[12] * m[3] * m[9];
        inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + m[8] * m[2] * m[13] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9];
        inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6];
        inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6];
        inv[10] = m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15] + m[4] * m[3] * m[13] + m[12] * m[1] * m[7] - m[12] * m[3] * m[5];
        inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5];
        inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6];
        inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6];
        inv[11] = -m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11] - m[4] * m[3] * m[9] - m[8] * m[1] * m[7] + m[8] * m[3] * m[5];
        inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5];

        float32 det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
        if (det == 0) return Identity();

        det = 1.0f / det;
        Matrix4x4 result;
        for (int i = 0; i < 16; i++) result.m[i] = inv[i] * det;
        return result;
    }

    void SetTranslation(const Vector3& translation) {
        m[12] = translation.x;
        m[13] = translation.y;
        m[14] = translation.z;
    }

    Vector3 GetTranslation() const {
        return Vector3(m[12], m[13], m[14]);
    }

    void SetScale(const Vector3& scale) {
        m[0] = scale.x;
        m[5] = scale.y;
        m[10] = scale.z;
    }

    Vector3 ExtractScale() const {
        return Vector3(m[0], m[5], m[10]);
    }

    Quaternion ExtractRotation() const {
        return Quaternion::FromLookRotation(Vector3(m[8], m[9], m[10]), Vector3(m[4], m[5], m[6]));
    }

    static Matrix4x4 Perspective(float32 fov, float32 aspect, float32 nearPlane, float32 farPlane) {
        Matrix4x4 result;
        float32 tanHalfFov = tanf(fov * 0.5f);
        result.m[0] = 1.0f / (aspect * tanHalfFov);
        result.m[5] = 1.0f / tanHalfFov;
        result.m[10] = (farPlane + nearPlane) / (nearPlane - farPlane);
        result.m[11] = -1.0f;
        result.m[14] = (2.0f * farPlane * nearPlane) / (nearPlane - farPlane);
        return result;
    }

    static Matrix4x4 LookAt(const Vector3& eye, const Vector3& target, const Vector3& up) {
        Vector3 f = (target - eye).Normalized();
        Vector3 s = Vector3::Cross(f, up).Normalized();
        Vector3 u = Vector3::Cross(s, f);

        Matrix4x4 result;
        result.m[0] = s.x; result.m[4] = s.y; result.m[8] = s.z;
        result.m[1] = u.x; result.m[5] = u.y; result.m[9] = u.z;
        result.m[2] = -f.x; result.m[6] = -f.y; result.m[10] = -f.z;
        result.m[12] = -Vector3::Dot(s, eye);
        result.m[13] = -Vector3::Dot(u, eye);
        result.m[14] = Vector3::Dot(f, eye);
        return result;
    }
};

}

#endif
