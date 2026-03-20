add_library(core_memory INTERFACE)
target_include_directories(core_memory INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(core_memory INTERFACE core_types core_object)
target_sources(core_memory INTERFACE
    SmartPtr.h SmartPtr.cpp
)