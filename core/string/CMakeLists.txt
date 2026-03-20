add_library(core_string INTERFACE)
target_include_directories(core_string INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(core_string INTERFACE core_types)
target_sources(core_string INTERFACE
    String.h String.cpp StringHash.h StringHash.cpp
)