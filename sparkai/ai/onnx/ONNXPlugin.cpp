#include "ONNXPlugin.h"

#ifdef SPARKAI_ORT_ENABLED

namespace SparkLabs {

ONNXPlugin::ONNXPlugin() {
}

ONNXPlugin::~ONNXPlugin() {
}

Vector<ONNXPlugin::CustomOpRegistry>& ONNXPlugin::GetGlobalRegistry() {
    static Vector<CustomOpRegistry> registry;
    return registry;
}

bool ONNXPlugin::RegisterCustomOps() {
    return true;
}

bool ONNXPlugin::RegisterCustomOp(const String& opType, OrtKernelComputeFunc computeFunc, void* opKernel) {
    CustomOpRegistry entry;
    entry.opType = opType;
    entry.computeFunc = computeFunc;
    entry.opKernel = opKernel;

    GetGlobalRegistry().PushBack(entry);
    return true;
}

bool ONNXPlugin::IsCustomOpRegistered(const String& opType) {
    const Vector<CustomOpRegistry>& registry = GetGlobalRegistry();
    for (size_t i = 0; i < registry.Size(); ++i) {
        if (registry[i].opType == opType) {
            return true;
        }
    }
    return false;
}

}

#endif
