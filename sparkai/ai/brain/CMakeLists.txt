add_library(ai_brain OBJECT)

target_sources(ai_brain PRIVATE
    TensorRef.h
    AIMemoryEntry.h
    AIBlackboard.h
    AIBlackboard.cpp
    AIEventBus.h
    AIEventBus.cpp
    AINode.h
    AINode.cpp
    NeuralNetwork.h
    NeuralNetwork.cpp
    AIBrain.h
    AIBrain.cpp
)

target_include_directories(ai_brain PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(ai_brain PUBLIC
    core_object
    core_memory
    core_string
    core_io
    engine_scene
)