add_library(SparkLabsEditor STATIC
    SceneEditor.h
    SceneEditor.cpp
    AIEditorPanel.h
    AIEditorPanel.cpp
    BehaviorTreeEditor.h
    BehaviorTreeEditor.cpp
    AssetBrowser.h
    AssetBrowser.cpp
    AssetGeneratorPanel.h
    AssetGeneratorPanel.cpp
)

target_link_libraries(SparkLabsEditor PUBLIC
    SparkLabs::Core
    SparkLabs::Engine
    SparkLabs::SparkLabs
)

target_include_directories(SparkLabsEditor PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

add_library(SparkLabs::Editor ALIAS SparkLabsEditor)
