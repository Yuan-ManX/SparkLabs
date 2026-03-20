#include "GPUSupport.h"

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/providers/cuda/cuda_provider_factory.h>
#include <onnxruntime/core/providers/metal/metal_provider_factory.h>
#include <onnxruntime/core/providers/cpu/cpu_provider_factory.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED

GPUSupport::GPUSupport()
    : m_CurrentBackend(GPUBackend::None)
    , m_DeviceId(0)
    , m_GPUHandle(nullptr)
    , m_OrtEnv(nullptr) {
}

GPUSupport::~GPUSupport() {
    m_GPUHandle = nullptr;
    m_OrtEnv = nullptr;
}

bool GPUSupport::IsAvailable(GPUBackend backend) {
    switch (backend) {
        case GPUBackend::CUDA: {
            std::vector<std::string> cuda_provider_options;
            size_t cuda_available = 0;
            Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_CUDA(
                nullptr, 0));
            return true;
        }
        case GPUBackend::Metal: {
            return true;
        }
        case GPUBackend::Vulkan:
        case GPUBackend::OpenCL:
        default:
            return false;
    }
}

void GPUSupport::InitializeGPU(GPUBackend backend, int32 deviceId) {
    m_CurrentBackend = backend;
    m_DeviceId = deviceId;

    switch (backend) {
        case GPUBackend::CUDA:
            m_GPUHandle = nullptr;
            break;
        case GPUBackend::Metal:
            m_GPUHandle = nullptr;
            break;
        case GPUBackend::Vulkan:
        case GPUBackend::OpenCL:
        case GPUBackend::None:
        default:
            m_CurrentBackend = GPUBackend::None;
            m_GPUHandle = nullptr;
            break;
    }
}

TensorRef GPUSupport::CopyToGPU(const TensorRef& cpuTensor) {
    if (!cpuTensor || cpuTensor->IsGPU()) {
        return cpuTensor;
    }

    TensorRef gpuTensor = new Tensor(cpuTensor->GetShape(), cpuTensor->GetDataType());

    size_t numBytes = cpuTensor->GetNumBytes();
    if (numBytes > 0 && cpuTensor->GetDataType() == Tensor::DataType::Float32) {
        const float32* srcData = cpuTensor->GetData<float32>();
        float32* dstData = gpuTensor->GetData<float32>();
        for (size_t i = 0; i < cpuTensor->GetNumElements(); ++i) {
            dstData[i] = srcData[i];
        }
    }

    gpuTensor->SetGPU(true);
    return gpuTensor;
}

TensorRef GPUSupport::CopyFromGPU(const TensorRef& gpuTensor) {
    if (!gpuTensor || !gpuTensor->IsGPU()) {
        return gpuTensor;
    }

    TensorRef cpuTensor = new Tensor(gpuTensor->GetShape(), gpuTensor->GetDataType());

    size_t numBytes = gpuTensor->GetNumBytes();
    if (numBytes > 0 && gpuTensor->GetDataType() == Tensor::DataType::Float32) {
        const float32* srcData = gpuTensor->GetData<float32>();
        float32* dstData = cpuTensor->GetData<float32>();
        for (size_t i = 0; i < gpuTensor->GetNumElements(); ++i) {
            dstData[i] = srcData[i];
        }
    }

    cpuTensor->SetGPU(false);
    return cpuTensor;
}

void* GPUSupport::GetGPUHandle() {
    return m_GPUHandle;
}

#else

bool GPUSupport::IsAvailable(GPUBackend) {
    return false;
}

void GPUSupport::InitializeGPU(GPUBackend, int32) {
}

TensorRef GPUSupport::CopyToGPU(const TensorRef& cpuTensor) {
    return cpuTensor;
}

TensorRef GPUSupport::CopyFromGPU(const TensorRef& gpuTensor) {
    return gpuTensor;
}

void* GPUSupport::GetGPUHandle() {
    return nullptr;
}

#endif

}
