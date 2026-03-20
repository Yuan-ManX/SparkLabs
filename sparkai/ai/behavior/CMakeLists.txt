add_library(ai_behavior
    BehaviorTreeNode.cpp
    CompositeNodes.cpp
    DecoratorNodes.cpp
    ActionNodes.cpp
    BehaviorTree.cpp
    Agent.cpp
    BehaviorTreeFactory.cpp
)

target_include_directories(ai_behavior PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(ai_behavior PRIVATE
    ${CMAKE_SOURCE_DIR}/core
    ${CMAKE_SOURCE_DIR}/engine/scene
)