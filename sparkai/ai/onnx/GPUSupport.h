#pragma once

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "Tensor.h"

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/session/onnxruntime_cxx_api.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED
class GPUSupport {
public:
    enum class GPUBackend {
        None,
        CUDA,
        Metal,
        Vulkan,
        OpenCL
    };

    GPUSupport();
    ~GPUSupport();

    static bool IsAvailable(GPUBackend backend);
    void InitializeGPU(GPUBackend backend, int32 deviceId = 0);
    TensorRef CopyToGPU(const TensorRef& cpuTensor);
    TensorRef CopyFromGPU(const TensorRef& gpuTensor);
    void* GetGPUHandle();
    GPUBackend GetCurrentBackend() const { return m_CurrentBackend; }
    int32 GetDeviceId() const { return m_DeviceId; }

private:
    GPUBackend m_CurrentBackend;
    int32 m_DeviceId;
    void* m_GPUHandle;
    Ort::Env* m_OrtEnv;
};
#else
class GPUSupport {
public:
    enum class GPUBackend {
        None,
        CUDA,
        Metal,
        Vulkan,
        OpenCL
    };

    GPUSupport() : m_CurrentBackend(GPUBackend::None), m_DeviceId(0), m_GPUHandle(nullptr) {}
    ~GPUSupport() {}

    static bool IsAvailable(GPUBackend backend) {
        (void)backend;
        return false;
    }
    void InitializeGPU(GPUBackend backend, int32 deviceId = 0) {
        (void)backend;
        (void)deviceId;
        m_CurrentBackend = GPUBackend::None;
        m_DeviceId = 0;
    }
    TensorRef CopyToGPU(const TensorRef& cpuTensor) { return cpuTensor; }
    TensorRef CopyFromGPU(const TensorRef& gpuTensor) { return gpuTensor; }
    void* GetGPUHandle() { return nullptr; }
    GPUBackend GetCurrentBackend() const { return m_CurrentBackend; }
    int32 GetDeviceId() const { return m_DeviceId; }

private:
    GPUBackend m_CurrentBackend;
    int32 m_DeviceId;
    void* m_GPUHandle;
};
#endif

}
