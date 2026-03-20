add_library(core_object INTERFACE)
target_include_directories(core_object INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(core_object INTERFACE core_types core_memory core_string)
target_sources(core_object INTERFACE
    Object.h Object.cpp
)