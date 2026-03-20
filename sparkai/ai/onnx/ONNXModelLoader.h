#pragma once

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "Tensor.h"

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/session/onnxruntime_cxx_api.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED

struct ModelMetadata {
    String name;
    String version;
    Vector<int64_t> inputShapes;
    Vector<int64_t> outputShapes;
};

class ONNXModelLoader {
public:
    ONNXModelLoader();
    ~ONNXModelLoader();

    static ModelMetadata GetModelMetadata(const String& modelPath);
    static bool ValidateModel(const String& modelPath);
    static Vector<String> GetInputNames(const String& modelPath);
    static Vector<String> GetOutputNames(const String& modelPath);

private:
    static Ort::Env& GetSharedEnv();
};

#else

struct ModelMetadata {
    String name;
    String version;
    Vector<int64_t> inputShapes;
    Vector<int64_t> outputShapes;
};

class ONNXModelLoader {
public:
    ONNXModelLoader() {}
    ~ONNXModelLoader() {}

    static ModelMetadata GetModelMetadata(const String& modelPath) {
        (void)modelPath;
        return ModelMetadata();
    }
    static bool ValidateModel(const String& modelPath) {
        (void)modelPath;
        return false;
    }
    static Vector<String> GetInputNames(const String& modelPath) {
        (void)modelPath;
        return Vector<String>();
    }
    static Vector<String> GetOutputNames(const String& modelPath) {
        (void)modelPath;
        return Vector<String>();
    }
};

#endif

}
