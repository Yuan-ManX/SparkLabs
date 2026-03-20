add_library(ai_brain_lib INTERFACE)
target_link_libraries(ai_brain_lib INTERFACE ai_brain)

add_library(ai INTERFACE)
target_include_directories(ai INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

add_subdirectory(brain)
add_subdirectory(behavior)