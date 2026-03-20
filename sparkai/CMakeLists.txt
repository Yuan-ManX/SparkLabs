add_library(sparkai STATIC
    ai/CMakeLists.txt
    npc/CMakeLists.txt
    gameplay/CMakeLists.txt
    narrative/CMakeLists.txt
    asset/CMakeLists.txt
    neural/CMakeLists.txt
    editor/CMakeLists.txt
)

target_link_libraries(sparkai PUBLIC
    SparkLabs::Core
    SparkLabs::Engine
    SparkLabs::Render
)

target_include_directories(sparkai PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

add_library(SparkLabs::sparkai ALIAS sparkai)
