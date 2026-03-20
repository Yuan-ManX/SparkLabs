add_library(core_math INTERFACE)
target_include_directories(core_math INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(core_math INTERFACE core_types)
target_sources(core_math INTERFACE
    Vector2.h Vector2.cpp
    Vector3.h Vector3.cpp
    Vector4.h Vector4.cpp
    Quaternion.h Quaternion.cpp
    Matrix4x4.h Matrix4x4.cpp
)