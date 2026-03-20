add_library(onnx INTERFACE)
target_include_directories(onnx INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

target_compile_definitions(onnx INTERFACE SPARKAI_ORT_ENABLED)

find_package(ONNXRuntime)
if(ONNXRuntime_FOUND)
    target_include_directories(onnx INTERFACE ${ONNXRuntime_INCLUDE_DIRS})
    target_link_libraries(onnx INTERFACE ${ONNXRuntime_LIBRARIES})
endif()