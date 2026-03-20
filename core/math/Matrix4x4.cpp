#include "math/Matrix4x4.h"
#include <cmath>
#include <algorithm>

namespace SparkLabs {

Matrix4x4::Matrix4x4() {
    m[0] = m[5] = m[10] = m[15] = 1.0f;
    m[1] = m[2] = m[3] = m[4] = m[6] = m[7] = m[8] = m[9] = m[11] = m[12] = m[13] = m[14] = 0.0f;
}

Matrix4x4::Matrix4x4(float32 m0, float32 m4, float32 m8,  float32 m12,
                     float32 m1, float32 m5, float32 m9,  float32 m13,
                     float32 m2, float32 m6, float32 m10, float32 m14,
                     float32 m3, float32 m7, float32 m11, float32 m15) {
    m[0] = m0;  m[4] = m4;  m[8] = m8;  m[12] = m12;
    m[1] = m1;  m[5] = m5;  m[9] = m9;  m[13] = m13;
    m[2] = m2;  m[6] = m6;  m[10] = m10; m[14] = m14;
    m[3] = m3;  m[7] = m7;  m[11] = m11; m[15] = m15;
}

Matrix4x4::Matrix4x4(const Matrix4x4& other) {
    for (int i = 0; i < 16; ++i) {
        m[i] = other.m[i];
    }
}

Matrix4x4& Matrix4x4::operator=(const Matrix4x4& other) {
    if (this != &other) {
        for (int i = 0; i < 16; ++i) {
            m[i] = other.m[i];
        }
    }
    return *this;
}

Matrix4x4 Matrix4x4::operator*(const Matrix4x4& other) const {
    return Multiply(*this, other);
}

Matrix4x4& Matrix4x4::operator*=(const Matrix4x4& other) {
    *this = Multiply(*this, other);
    return *this;
}

Vector4 Matrix4x4::operator*(const Vector4& v) const {
    return Vector4(
        m[0] * v.x + m[4] * v.y + m[8]  * v.z + m[12] * v.w,
        m[1] * v.x + m[5] * v.y + m[9]  * v.z + m[13] * v.w,
        m[2] * v.x + m[6] * v.y + m[10] * v.z + m[14] * v.w,
        m[3] * v.x + m[7] * v.y + m[11] * v.z + m[15] * v.w
    );
}

Vector3 Matrix4x4::operator*(const Vector3& v) const {
    return Vector3(
        m[0] * v.x + m[4] * v.y + m[8]  * v.z + m[12],
        m[1] * v.x + m[5] * v.y + m[9]  * v.z + m[13],
        m[2] * v.x + m[6] * v.y + m[10] * v.z + m[14]
    );
}

bool Matrix4x4::operator==(const Matrix4x4& other) const {
    for (int i = 0; i < 16; ++i) {
        if (m[i] != other.m[i]) return false;
    }
    return true;
}

bool Matrix4x4::operator!=(const Matrix4x4& other) const {
    return !(*this == other);
}

float32 Matrix4x4::Determinant() const {
    float32 det = 0.0f;
    det = m[0] * (m[5] * (m[10] * m[15] - m[11] * m[14]) - m[9] * (m[6] * m[15] - m[7] * m[14]) + m[13] * (m[6] * m[11] - m[7] * m[10]))
         - m[4] * (m[1] * (m[10] * m[15] - m[11] * m[14]) - m[9] * (m[2] * m[15] - m[3] * m[14]) + m[13] * (m[2] * m[11] - m[3] * m[10]))
         + m[8] * (m[1] * (m[6] * m[15] - m[7] * m[14]) - m[5] * (m[2] * m[15] - m[3] * m[14]) + m[13] * (m[2] * m[7] - m[3] * m[6]))
         - m[12] * (m[1] * (m[6] * m[11] - m[7] * m[10]) - m[5] * (m[2] * m[11] - m[3] * m[10]) + m[9] * (m[2] * m[7] - m[3] * m[6]));
    return det;
}

Matrix4x4 Matrix4x4::Transpose() const {
    return Transpose(*this);
}

Matrix4x4 Matrix4x4::Inverse() const {
    return Inverse(*this);
}

Matrix4x4 Matrix4x4::Identity() {
    return Matrix4x4();
}

Matrix4x4 Matrix4x4::Multiply(const Matrix4x4& a, const Matrix4x4& b) {
    Matrix4x4 result;
    for (int row = 0; row < 4; ++row) {
        for (int col = 0; col < 4; ++col) {
            result.m[row + col * 4] =
                a.m[row + 0 * 4] * b.m[0 + col * 4] +
                a.m[row + 1 * 4] * b.m[1 + col * 4] +
                a.m[row + 2 * 4] * b.m[2 + col * 4] +
                a.m[row + 3 * 4] * b.m[3 + col * 4];
        }
    }
    return result;
}

Matrix4x4 Matrix4x4::Transpose(const Matrix4x4& mat) {
    Matrix4x4 result;
    for (int row = 0; row < 4; ++row) {
        for (int col = 0; col < 4; ++col) {
            result.m[row + col * 4] = mat.m[col + row * 4];
        }
    }
    return result;
}

Matrix4x4 Matrix4x4::Inverse(const Matrix4x4& mat) {
    Matrix4x4 result;
    float32 invDet = 1.0f / mat.Determinant();

    result.m[0] = mat.m[5] * (mat.m[10] * mat.m[15] - mat.m[11] * mat.m[14]) - mat.m[9] * (mat.m[6] * mat.m[15] - mat.m[7] * mat.m[14]) + mat.m[13] * (mat.m[6] * mat.m[11] - mat.m[7] * mat.m[10]);
    result.m[4] = -(mat.m[4] * (mat.m[10] * mat.m[15] - mat.m[11] * mat.m[14]) - mat.m[8] * (mat.m[6] * mat.m[15] - mat.m[7] * mat.m[14]) + mat.m[12] * (mat.m[6] * mat.m[11] - mat.m[7] * mat.m[10]));
    result.m[8] = mat.m[4] * (mat.m[9] * mat.m[15] - mat.m[11] * mat.m[13]) - mat.m[8] * (mat.m[5] * mat.m[15] - mat.m[7] * mat.m[13]) + mat.m[12] * (mat.m[5] * mat.m[11] - mat.m[7] * mat.m[9]);
    result.m[12] = -(mat.m[4] * (mat.m[9] * mat.m[14] - mat.m[10] * mat.m[13]) - mat.m[8] * (mat.m[5] * mat.m[14] - mat.m[7] * mat.m[13]) + mat.m[12] * (mat.m[5] * mat.m[10] - mat.m[6] * mat.m[9]));

    result.m[1] = -(mat.m[1] * (mat.m[10] * mat.m[15] - mat.m[11] * mat.m[14]) - mat.m[9] * (mat.m[2] * mat.m[15] - mat.m[3] * mat.m[14]) + mat.m[13] * (mat.m[2] * mat.m[11] - mat.m[3] * mat.m[10]));
    result.m[5] = mat.m[0] * (mat.m[10] * mat.m[15] - mat.m[11] * mat.m[14]) - mat.m[8] * (mat.m[2] * mat.m[15] - mat.m[3] * mat.m[14]) + mat.m[12] * (mat.m[2] * mat.m[11] - mat.m[3] * mat.m[10]);
    result.m[9] = -(mat.m[0] * (mat.m[9] * mat.m[15] - mat.m[11] * mat.m[13]) - mat.m[8] * (mat.m[1] * mat.m[15] - mat.m[3] * mat.m[13]) + mat.m[12] * (mat.m[1] * mat.m[11] - mat.m[3] * mat.m[9]));
    result.m[13] = mat.m[0] * (mat.m[9] * mat.m[14] - mat.m[10] * mat.m[13]) - mat.m[8] * (mat.m[1] * mat.m[14] - mat.m[3] * mat.m[13]) + mat.m[12] * (mat.m[1] * mat.m[10] - mat.m[2] * mat.m[9]);

    result.m[2] = mat.m[1] * (mat.m[6] * mat.m[15] - mat.m[7] * mat.m[14]) - mat.m[5] * (mat.m[2] * mat.m[15] - mat.m[3] * mat.m[14]) + mat.m[13] * (mat.m[2] * mat.m[7] - mat.m[3] * mat.m[6]);
    result.m[6] = -(mat.m[0] * (mat.m[6] * mat.m[15] - mat.m[7] * mat.m[14]) - mat.m[4] * (mat.m[2] * mat.m[15] - mat.m[3] * mat.m[14]) + mat.m[12] * (mat.m[2] * mat.m[7] - mat.m[3] * mat.m[6]));
    result.m[10] = mat.m[0] * (mat.m[5] * mat.m[15] - mat.m[7] * mat.m[13]) - mat.m[4] * (mat.m[1] * mat.m[15] - mat.m[3] * mat.m[13]) + mat.m[12] * (mat.m[1] * mat.m[7] - mat.m[3] * mat.m[5]);
    result.m[14] = -(mat.m[0] * (mat.m[5] * mat.m[14] - mat.m[6] * mat.m[13]) - mat.m[4] * (mat.m[1] * mat.m[14] - mat.m[3] * mat.m[13]) + mat.m[12] * (mat.m[1] * mat.m[6] - mat.m[2] * mat.m[5]));

    result.m[3] = -(mat.m[1] * (mat.m[6] * mat.m[11] - mat.m[7] * mat.m[10]) - mat.m[5] * (mat.m[2] * mat.m[11] - mat.m[3] * mat.m[10]) + mat.m[9] * (mat.m[2] * mat.m[7] - mat.m[3] * mat.m[6]));
    result.m[7] = mat.m[0] * (mat.m[6] * mat.m[11] - mat.m[7] * mat.m[10]) - mat.m[4] * (mat.m[2] * mat.m[11] - mat.m[3] * mat.m[10]) + mat.m[8] * (mat.m[2] * mat.m[7] - mat.m[3] * mat.m[6]);
    result.m[11] = -(mat.m[0] * (mat.m[5] * mat.m[11] - mat.m[7] * mat.m[9]) - mat.m[4] * (mat.m[1] * mat.m[11] - mat.m[3] * mat.m[9]) + mat.m[8] * (mat.m[1] * mat.m[7] - mat.m[3] * mat.m[5]));
    result.m[15] = mat.m[0] * (mat.m[5] * mat.m[10] - mat.m[6] * mat.m[9]) - mat.m[4] * (mat.m[1] * mat.m[10] - mat.m[2] * mat.m[9]) + mat.m[8] * (mat.m[1] * mat.m[6] - mat.m[2] * mat.m[5]);

    for (int i = 0; i < 16; ++i) {
        result.m[i] *= invDet;
    }

    return result;
}

Matrix4x4 Matrix4x4::Perspective(float32 fov, float32 aspect, float32 near, float32 far) {
    Matrix4x4 result;
    float32 tanHalfFov = std::tan(fov / 2.0f);
    result.m[0] = 1.0f / (aspect * tanHalfFov);
    result.m[5] = 1.0f / tanHalfFov;
    result.m[10] = -(far + near) / (far - near);
    result.m[11] = -1.0f;
    result.m[14] = -(2.0f * far * near) / (far - near);
    result.m[15] = 0.0f;
    return result;
}

Matrix4x4 Matrix4x4::LookAt(const Vector3& eye, const Vector3& target, const Vector3& up) {
    Vector3 zAxis = (eye - target).Normalize();
    Vector3 xAxis = up.Cross(zAxis).Normalize();
    Vector3 yAxis = zAxis.Cross(xAxis);

    Matrix4x4 result;
    result.m[0] = xAxis.x; result.m[4] = xAxis.y; result.m[8] = xAxis.z;  result.m[12] = -xAxis.Dot(eye);
    result.m[1] = yAxis.x; result.m[5] = yAxis.y; result.m[9] = yAxis.z;  result.m[13] = -yAxis.Dot(eye);
    result.m[2] = zAxis.x; result.m[6] = zAxis.y; result.m[10] = zAxis.z; result.m[14] = -zAxis.Dot(eye);
    result.m[3] = 0.0f; result.m[7] = 0.0f; result.m[11] = 0.0f; result.m[15] = 1.0f;
    return result;
}

Matrix4x4 Matrix4x4::Translate(const Vector3& translation) {
    Matrix4x4 result;
    result.m[12] = translation.x;
    result.m[13] = translation.y;
    result.m[14] = translation.z;
    return result;
}

Matrix4x4 Matrix4x4::Scale(const Vector3& scale) {
    Matrix4x4 result;
    result.m[0] = scale.x;
    result.m[5] = scale.y;
    result.m[10] = scale.z;
    return result;
}

Matrix4x4 Matrix4x4::Rotate(const Quaternion& rotation) {
    return rotation.ToMatrix();
}

Matrix4x4 Matrix4x4::Transform(const Vector3& translation, const Quaternion& rotation, const Vector3& scale) {
    Matrix4x4 result = Scale(scale) * rotation.ToMatrix();
    result.m[12] = translation.x;
    result.m[13] = translation.y;
    result.m[14] = translation.z;
    return result;
}

float32 Matrix4x4::Get(int row, int col) const {
    return m[row + col * 4];
}

void Matrix4x4::Set(int row, int col, float32 value) {
    m[row + col * 4] = value;
}

}
