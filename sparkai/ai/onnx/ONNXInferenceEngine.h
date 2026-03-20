#pragma once

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "Tensor.h"
#include "GPUSupport.h"
#include "MemoryPool.h"
#include "ONNXPlugin.h"

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/session/onnxruntime_cxx_api.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED

class ONNXInferenceEngine : public ONNXPlugin {
public:
    enum class GraphOptimizationLevel {
        None = 0,
        Basic = 1,
        Extended = 2,
        Full = 3
    };

    ONNXInferenceEngine();
    ~ONNXInferenceEngine() override;

    bool Initialize(const String& modelPath, const String& gpuDevice = "");
    TensorRef Run(const String& inputName, const TensorRef& inputTensor);
    Vector<TensorRef> RunBatch(const Vector< std::pair<String, TensorRef> >& inputs);
    void SetIntraOpThreads(int32 numThreads);
    void SetGraphOptimizationLevel(GraphOptimizationLevel level);

    const Vector<String>& GetInputNames() const { return m_InputNames; }
    const Vector<String>& GetOutputNames() const { return m_OutputNames; }
    bool IsInitialized() const { return m_Initialized; }

private:
    Ort::Env m_Env;
    Ort::Session m_Session;
    Ort::SessionOptions m_SessionOptions;
    Vector<String> m_InputNames;
    Vector<String> m_OutputNames;
    bool m_Initialized;
    GPUSupport m_GPUSupport;
    MemoryPool m_MemoryPool;
    GraphOptimizationLevel m_OptimizationLevel;

    void CreateSessionOptions();
    void ConfigureGPU(const String& gpuDevice);
    TensorRef RunInternal(const Vector<String>& inputNames, const Vector<TensorRef>& inputTensors);
};

#else

class ONNXInferenceEngine : public ONNXPlugin {
public:
    enum class GraphOptimizationLevel {
        None = 0,
        Basic = 1,
        Extended = 2,
        Full = 3
    };

    ONNXInferenceEngine() : m_Initialized(false), m_OptimizationLevel(GraphOptimizationLevel::None) {}
    ~ONNXInferenceEngine() override {}

    bool Initialize(const String& modelPath, const String& gpuDevice = "") {
        (void)modelPath;
        (void)gpuDevice;
        return false;
    }

    TensorRef Run(const String& inputName, const TensorRef& inputTensor) {
        (void)inputName;
        (void)inputTensor;
        return nullptr;
    }

    Vector<TensorRef> RunBatch(const Vector< Pair<String, TensorRef> >& inputs) {
        (void)inputs;
        return Vector<TensorRef>();
    }

    void SetIntraOpThreads(int32 numThreads) { (void)numThreads; }
    void SetGraphOptimizationLevel(GraphOptimizationLevel level) { m_OptimizationLevel = level; }

    const Vector<String>& GetInputNames() const { return m_InputNames; }
    const Vector<String>& GetOutputNames() const { return m_OutputNames; }
    bool IsInitialized() const { return m_Initialized; }

private:
    Vector<String> m_InputNames;
    Vector<String> m_OutputNames;
    bool m_Initialized;
    GraphOptimizationLevel m_OptimizationLevel;
};

#endif

}
