#include "ONNXModelLoader.h"

#ifdef SPARKAI_ORT_ENABLED
#include <fstream>
#include <cstring>

namespace SparkLabs {

static Ort::Env* s_Env = nullptr;

ONNXModelLoader::ONNXModelLoader() {
}

ONNXModelLoader::~ONNXModelLoader() {
}

Ort::Env& ONNXModelLoader::GetSharedEnv() {
    if (s_Env == nullptr) {
        s_Env = new Ort::Env(ORT_LOGGING_LEVEL_WARNING, "SparkLabs-ONNX");
    }
    return *s_Env;
}

ModelMetadata ONNXModelLoader::GetModelMetadata(const String& modelPath) {
    ModelMetadata metadata;

    if (!ValidateModel(modelPath)) {
        return metadata;
    }

    try {
        Ort::Session session(GetSharedEnv(), modelPath.C_str(), Ort::SessionOptions{nullptr});

        size_t numInputNodes = session.GetInputCount();
        size_t numOutputNodes = session.GetOutputCount();

        metadata.inputShapes.Resize(numInputNodes);
        metadata.outputShapes.Resize(numOutputNodes);

        for (size_t i = 0; i < numInputNodes; ++i) {
            auto inputName = session.GetInputNameAllocated(i, Ort::AllocatorWithDefaultOptions{});
            auto inputTypeInfo = session.GetInputTypeInfo(i);
            auto inputShapeInfo = inputTypeInfo.GetTensorTypeAndShapeInfo();

            metadata.inputShapes[i] = 0;
            metadata.name = inputName.get();
        }

        for (size_t i = 0; i < numOutputNodes; ++i) {
            auto outputName = session.GetOutputNameAllocated(i, Ort::AllocatorWithDefaultOptions{});
            auto outputTypeInfo = session.GetOutputTypeInfo(i);
            auto outputShapeInfo = outputTypeInfo.GetTensorTypeAndShapeInfo();

            metadata.outputShapes[i] = 0;
        }

        metadata.version = "1.0";

    } catch (const std::exception& e) {
        (void)e;
    }

    return metadata;
}

bool ONNXModelLoader::ValidateModel(const String& modelPath) {
    if (modelPath.Empty()) {
        return false;
    }

    std::ifstream file(modelPath.C_str(), std::ios::binary);
    if (!file.is_open()) {
        return false;
    }

    file.seekg(0, std::ios::end);
    size_t fileSize = static_cast<size_t>(file.tellg());
    file.seekg(0, std::ios::beg);

    if (fileSize < 4) {
        return false;
    }

    char header[4];
    file.read(header, 4);

    bool isValidONNX = (std::strncmp(header, "ONNX", 4) == 0) ||
                       (std::strncmp(header, "8B", 2) == 0 && header[2] == 0);

    file.close();

    if (!isValidONNX) {
        try {
            Ort::Session session(GetSharedEnv(), modelPath.C_str(), Ort::SessionOptions{nullptr});
            isValidONNX = true;
        } catch (...) {
            isValidONNX = false;
        }
    }

    return isValidONNX;
}

Vector<String> ONNXModelLoader::GetInputNames(const String& modelPath) {
    Vector<String> inputNames;

    if (!ValidateModel(modelPath)) {
        return inputNames;
    }

    try {
        Ort::Session session(GetSharedEnv(), modelPath.C_str(), Ort::SessionOptions{nullptr});
        size_t numInputNodes = session.GetInputCount();

        inputNames.Resize(numInputNodes);

        for (size_t i = 0; i < numInputNodes; ++i) {
            auto inputName = session.GetInputNameAllocated(i, Ort::AllocatorWithDefaultOptions{});
            inputNames[i] = inputName.get();
        }

    } catch (const std::exception& e) {
        (void)e;
        inputNames.Clear();
    }

    return inputNames;
}

Vector<String> ONNXModelLoader::GetOutputNames(const String& modelPath) {
    Vector<String> outputNames;

    if (!ValidateModel(modelPath)) {
        return outputNames;
    }

    try {
        Ort::Session session(GetSharedEnv(), modelPath.C_str(), Ort::SessionOptions{nullptr});
        size_t numOutputNodes = session.GetOutputCount();

        outputNames.Resize(numOutputNodes);

        for (size_t i = 0; i < numOutputNodes; ++i) {
            auto outputName = session.GetOutputNameAllocated(i, Ort::AllocatorWithDefaultOptions{});
            outputNames[i] = outputName.get();
        }

    } catch (const std::exception& e) {
        (void)e;
        outputNames.Clear();
    }

    return outputNames;
}

}

#endif
