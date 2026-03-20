add_library(SparkLabsCore STATIC
    Types.h
    SparkObject.h
    Threading/Mutex.h
    Threading/Signal.h
    Threading/ThreadID.h
    io/Vector.h
    math/Vector2.h
    math/Vector2.cpp
    math/Vector3.h
    math/Vector3.cpp
    math/Vector4.h
    math/Vector4.cpp
    math/Matrix4x4.h
    math/Matrix4x4.cpp
    math/Quaternion.h
    math/Quaternion.cpp
    memory/SmartPtr.h
    memory/SmartPtr.cpp
    object/Object.h
    object/Object.cpp
    string/String.h
    string/String.cpp
    string/StringHash.h
    string/StringHash.cpp
)

target_include_directories(SparkLabsCore PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

add_library(SparkLabs::Core ALIAS SparkLabsCore)
