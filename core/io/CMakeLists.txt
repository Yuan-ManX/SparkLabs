add_library(core_io INTERFACE)
target_include_directories(core_io INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(core_io INTERFACE core_types)
target_sources(core_io INTERFACE
    Vector.h
)