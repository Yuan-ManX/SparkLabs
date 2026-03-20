#pragma once

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "Tensor.h"

#ifdef SPARKAI_ORT_ENABLED
#include <onnxruntime/core/session/onnxruntime_cxx_api.h>
#endif

namespace SparkLabs {

#ifdef SPARKAI_ORT_ENABLED

class ONNXPlugin {
public:
    ONNXPlugin();
    ~ONNXPlugin();

    virtual bool RegisterCustomOps();
    virtual bool RegisterCustomOp(const String& opType, OrtKernelComputeFunc computeFunc, void* opKernel);

    static bool IsCustomOpRegistered(const String& opType);

private:
    struct CustomOpRegistry {
        String opType;
        OrtKernelComputeFunc computeFunc;
        void* opKernel;
    };

    static Vector<CustomOpRegistry>& GetGlobalRegistry();
};

#else

class ONNXPlugin {
public:
    ONNXPlugin() {}
    ~ONNXPlugin() {}

    virtual bool RegisterCustomOps() { return false; }
    virtual bool RegisterCustomOp(const String& opType, void* computeFunc, void* opKernel) {
        (void)opType;
        (void)computeFunc;
        (void)opKernel;
        return false;
    }

    static bool IsCustomOpRegistered(const String& opType) {
        (void)opType;
        return false;
    }
};

#endif

}
