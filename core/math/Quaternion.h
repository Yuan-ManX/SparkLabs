#ifndef SPARKLABS_CORE_MATH_QUATERNION_H
#define SPARKLABS_CORE_MATH_QUATERNION_H

#include "../Types.h"
#include "Vector3.h"
#include <cmath>

namespace SparkLabs {

class Matrix4x4;

class Quaternion {
public:
    float32 x, y, z, w;

    Quaternion() : x(0.0f), y(0.0f), z(0.0f), w(1.0f) {}
    Quaternion(float32 x_, float32 y_, float32 z_, float32 w_) : x(x_), y(y_), z(z_), w(w_) {}

    static Quaternion Identity() { return Quaternion(0.0f, 0.0f, 0.0f, 1.0f); }

    static Quaternion FromEuler(float32 pitch, float32 yaw, float32 roll) {
        float32 cy = cosf(yaw * 0.5f);
        float32 sy = sinf(yaw * 0.5f);
        float32 cp = cosf(pitch * 0.5f);
        float32 sp = sinf(pitch * 0.5f);
        float32 cr = cosf(roll * 0.5f);
        float32 sr = sinf(roll * 0.5f);

        Quaternion q;
        q.w = cr * cp * cy + sr * sp * sy;
        q.x = sr * cp * cy - cr * sp * sy;
        q.y = cr * sp * cy + sr * cp * sy;
        q.z = cr * cp * sy - sr * sp * cy;
        return q;
    }

    static Quaternion FromLookRotation(const Vector3& forward, const Vector3& up) {
        Vector3 f = forward.Normalized();
        Vector3 r = Vector3::Cross(f, up).Normalized();
        Vector3 u = Vector3::Cross(r, f);

        float32 m00 = r.x, m01 = r.y, m02 = r.z;
        float32 m10 = u.x, m11 = u.y, m12 = u.z;
        float32 m20 = f.x, m21 = f.y, m22 = f.z;

        Quaternion q;
        float32 trace = m00 + m11 + m22;
        if (trace > 0.0f) {
            float32 s = sqrtf(trace + 1.0f) * 2.0f;
            q.w = 0.25f * s;
            q.x = (m21 - m12) / s;
            q.y = (m02 - m20) / s;
            q.z = (m10 - m01) / s;
        } else if (m00 > m11 && m00 > m22) {
            float32 s = sqrtf(1.0f + m00 - m11 - m22) * 2.0f;
            q.w = (m21 - m12) / s;
            q.x = 0.25f * s;
            q.y = (m01 + m10) / s;
            q.z = (m02 + m20) / s;
        } else if (m11 > m22) {
            float32 s = sqrtf(1.0f + m11 - m00 - m22) * 2.0f;
            q.w = (m02 - m20) / s;
            q.x = (m01 + m10) / s;
            q.y = 0.25f * s;
            q.z = (m12 + m21) / s;
        } else {
            float32 s = sqrtf(1.0f + m22 - m00 - m11) * 2.0f;
            q.w = (m10 - m01) / s;
            q.x = (m02 + m20) / s;
            q.y = (m12 + m21) / s;
            q.z = 0.25f * s;
        }

        return q.Normalized();
    }

    Quaternion operator*(const Quaternion& other) const {
        Quaternion result;
        result.w = w * other.w - x * other.x - y * other.y - z * other.z;
        result.x = w * other.x + x * other.w + y * other.z - z * other.y;
        result.y = w * other.y - x * other.z + y * other.w + z * other.x;
        result.z = w * other.z + x * other.y - y * other.x + z * other.w;
        return result;
    }

    Vector3 operator*(const Vector3& v) const {
        Quaternion qv(0.0f, v.x, v.y, v.z);
        Quaternion qconjugate = Quaternion(-x, -y, -z, w);
        Quaternion qresult = (*this) * qv * qconjugate;
        return Vector3(qresult.x, qresult.y, qresult.z);
    }

    float32 Dot(const Quaternion& other) const { return w * other.w + x * other.x + y * other.y + z * other.z; }

    Quaternion Normalized() const {
        float32 len = sqrtf(w * w + x * x + y * y + z * z);
        if (len > 0.0f) {
            return Quaternion(x / len, y / len, z / len, w / len);
        }
        return Identity();
    }

    Matrix4x4 ToMatrix() const;
};

}

#endif
