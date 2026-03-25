cmake_minimum_required(VERSION 3.15)

option(SPARKLABS_PYTHON_BINDINGS "Build Python bindings" ON)
option(SPARKLABS_PYTHON_VERSION "Python version to use" "3.8")

if(SPARKLABS_PYTHON_BINDINGS)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

    if(NOT TARGET sparklabs_bindings)
        add_library(sparklabs_bindings SHARED)
        target_sources(sparklabs_bindings PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/bindings/PyBindings.cpp
        )
        target_include_directories(sparklabs_bindings PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/bindings
            ${Python3_INCLUDE_DIRS}
        )
        target_link_libraries(sparklabs_bindings PRIVATE
            SparkLabs::Core
            SparkLabs::Engine
            SparkLabs::sparkai
            Python3::Python
        )
        target_compile_definitions(sparklabs_bindings PRIVATE
            SPARKLABS_PYTHON_BINDINGS
        )
        set_target_properties(sparklabs_bindings PROPERTIES
            PREFIX ""
            OUTPUT_NAME "sparklabs"
            LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/python
        )

        if(APPLE)
            set_target_properties(sparklabs_bindings PROPERTIES
                SUFFIX ".so"
            )
        endif()
    endif()
endif()

add_library(scripts INTERFACE)
target_include_directories(scripts INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
