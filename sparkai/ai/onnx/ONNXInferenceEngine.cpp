#include "ONNXInferenceEngine.h"
#include "ONNXModelLoader.h"
#include <algorithm>

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/providers/cuda/cuda_provider_factory.h>
#include <onnxruntime/core/providers/cpu/cpu_provider_factory.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED

ONNXInferenceEngine::ONNXInferenceEngine()
    : m_Initialized(false)
    , m_OptimizationLevel(GraphOptimizationLevel::Extended) {
    m_Env = Ort::Env(ORT_LOGGING_LEVEL_WARNING, "SparkLabs-ONNX-Inference");
}

ONNXInferenceEngine::~ONNXInferenceEngine() {
    m_Session = Ort::Session(nullptr);
    m_SessionOptions = Ort::SessionOptions(nullptr);
    m_InputNames.Clear();
    m_OutputNames.Clear();
}

bool ONNXInferenceEngine::Initialize(const String& modelPath, const String& gpuDevice) {
    if (modelPath.Empty()) {
        return false;
    }

    if (!ONNXModelLoader::ValidateModel(modelPath)) {
        return false;
    }

    try {
        CreateSessionOptions();

        ConfigureGPU(gpuDevice);

        RegisterCustomOps();

        m_Session = Ort::Session(m_Env, modelPath.C_str(), m_SessionOptions);

        m_InputNames = ONNXModelLoader::GetInputNames(modelPath);
        m_OutputNames = ONNXModelLoader::GetOutputNames(modelPath);

        m_Initialized = true;
        return true;

    } catch (const std::exception& e) {
        (void)e;
        m_Initialized = false;
        return false;
    }
}

void ONNXInferenceEngine::CreateSessionOptions() {
    m_SessionOptions = Ort::SessionOptions();

    switch (m_OptimizationLevel) {
        case GraphOptimizationLevel::None:
            m_SessionOptions.SetGraphOptimizationLevel(ORT_GRAPH_OPTIMIZATION_LEVEL_NONE);
            break;
        case GraphOptimizationLevel::Basic:
            m_SessionOptions.SetGraphOptimizationLevel(ORT_GRAPH_OPTIMIZATION_LEVEL_ORT_ENABLE_BASIC);
            break;
        case GraphOptimizationLevel::Extended:
            m_SessionOptions.SetGraphOptimizationLevel(ORT_GRAPH_OPTIMIZATION_LEVEL_ORT_ENABLE_EXTENDED);
            break;
        case GraphOptimizationLevel::Full:
            m_SessionOptions.SetGraphOptimizationLevel(ORT_GRAPH_OPTIMIZATION_LEVEL_ORT_ENABLE_ALL);
            break;
    }
}

void ONNXInferenceEngine::ConfigureGPU(const String& gpuDevice) {
    if (!gpuDevice.Empty()) {
        if (gpuDevice == "CUDA" || gpuDevice == "cuda") {
            if (GPUSupport::IsAvailable(GPUSupport::GPUBackend::CUDA)) {
                Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_CUDA(
                    m_SessionOptions, 0));
                m_GPUSupport.InitializeGPU(GPUSupport::GPUBackend::CUDA);
            }
        } else if (gpuDevice == "Metal" || gpuDevice == "metal") {
            if (GPUSupport::IsAvailable(GPUSupport::GPUBackend::Metal)) {
                m_GPUSupport.InitializeGPU(GPUSupport::GPUBackend::Metal);
            }
        }
    }
}

void ONNXInferenceEngine::SetIntraOpThreads(int32 numThreads) {
    if (numThreads > 0) {
        m_SessionOptions.SetIntraOpNumThreads(numThreads);
    }
}

void ONNXInferenceEngine::SetGraphOptimizationLevel(GraphOptimizationLevel level) {
    m_OptimizationLevel = level;
    if (m_Initialized) {
        CreateSessionOptions();
        ConfigureGPU("");
    }
}

TensorRef ONNXInferenceEngine::Run(const String& inputName, const TensorRef& inputTensor) {
    if (!m_Initialized || inputTensor == nullptr) {
        return nullptr;
    }

    Vector<String> inputNames;
    Vector<TensorRef> inputTensors;
    inputNames.PushBack(inputName);
    inputTensors.PushBack(inputTensor);

    return RunInternal(inputNames, inputTensors);
}

Vector<TensorRef> ONNXInferenceEngine::RunBatch(const Vector< std::pair<String, TensorRef> >& inputs) {
    Vector<TensorRef> outputs;

    if (!m_Initialized || inputs.Empty()) {
        return outputs;
    }

    Vector<String> inputNames;
    Vector<TensorRef> inputTensors;

    for (size_t i = 0; i < inputs.Size(); ++i) {
        inputNames.PushBack(inputs[i].first);
        inputTensors.PushBack(inputs[i].second);
    }

    TensorRef result = RunInternal(inputNames, inputTensors);
    if (result != nullptr) {
        outputs.PushBack(result);
    }

    return outputs;
}

TensorRef ONNXInferenceEngine::RunInternal(const Vector<String>& inputNames, const Vector<TensorRef>& inputTensors) {
    if (inputNames.Size() != inputTensors.Size()) {
        return nullptr;
    }

    try {
        std::vector<const char*> inputNamesCStr;
        std::vector<const char*> outputNamesCStr;
        std::vector<Ort::Value> inputValues;

        for (size_t i = 0; i < inputNames.Size(); ++i) {
            inputNamesCStr.push_back(inputNames[i].C_str());
        }

        for (size_t i = 0; i < m_OutputNames.Size(); ++i) {
            outputNamesCStr.push_back(m_OutputNames[i].C_str());
        }

        for (size_t i = 0; i < inputTensors.Size(); ++i) {
            TensorRef tensor = inputTensors[i];
            if (tensor == nullptr) continue;

            std::vector<int64_t> shape;
            const Vector<size_t>& tensorShape = tensor->GetShape();
            for (size_t j = 0; j < tensorShape.Size(); ++j) {
                shape.push_back(static_cast<int64_t>(tensorShape[j]));
            }

            ONNXTensorElementDataType onnxType;
            switch (tensor->GetDataType()) {
                case Tensor::DataType::Float32:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
                    break;
                case Tensor::DataType::Float64:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_DOUBLE;
                    break;
                case Tensor::DataType::Int32:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_INT32;
                    break;
                case Tensor::DataType::Int64:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
                    break;
                case Tensor::DataType::UInt8:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_UINT8;
                    break;
                case Tensor::DataType::Int8:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_INT8;
                    break;
                default:
                    onnxType = ONNXTensorElementDataType::ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
                    break;
            }

            inputValues.push_back(Ort::Value::CreateTensor(
                Ort::AllocatorWithDefaultOptions(),
                shape.data(),
                shape.size(),
                onnxType));
        }

        auto outputValues = m_Session.Run(
            Ort::RunOptions{nullptr},
            inputNamesCStr.data(),
            inputValues.data(),
            inputValues.size(),
            outputNamesCStr.data(),
            outputNamesCStr.size());

        if (outputValues.empty()) {
            return nullptr;
        }

        Ort::Value& outputValue = outputValues[0];
        auto outputShapeInfo = outputValue.GetTensorTypeAndShapeInfo();
        std::vector<int64_t> outputShape = outputShapeInfo.GetShape();

        TensorRef resultTensor = m_MemoryPool.Allocate(
            Vector<size_t>(outputShape.size(), 0),
            Tensor::DataType::Float32);

        for (size_t i = 0; i < outputShape.size(); ++i) {
            resultTensor->Reshape(Vector<size_t>(outputShape.size(), 0));
        }

        return resultTensor;

    } catch (const std::exception& e) {
        (void)e;
        return nullptr;
    }
}

#endif

}
