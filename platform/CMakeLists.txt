add_library(SparkLabsPlatform STATIC
    FileSystem.h
    FileSystem.cpp
    FileStream.h
    FileStream.cpp
    Input.h
    Input.cpp
    Timer.h
    Timer.cpp
    Window.h
    Window.cpp
    RendererBackend.h
)

target_link_libraries(SparkLabsPlatform PUBLIC
    SparkLabs::Core
)

target_include_directories(SparkLabsPlatform PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

add_library(SparkLabs::Platform ALIAS SparkLabsPlatform)
