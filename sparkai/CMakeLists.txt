add_library(sparkai STATIC
    ai/behavior/ActionNodes.cpp
    ai/behavior/Agent.cpp
    ai/behavior/BehaviorTree.cpp
    ai/behavior/BehaviorTreeFactory.cpp
    ai/behavior/BehaviorTreeNode.cpp
    ai/behavior/CompositeNodes.cpp
    ai/behavior/DecoratorNodes.cpp
    ai/brain/AIBlackboard.cpp
    ai/brain/AIBrain.cpp
    ai/brain/AIEventBus.cpp
    ai/brain/AINode.cpp
    ai/brain/NeuralNetwork.cpp
    ai/onnx/GPUSupport.cpp
    ai/onnx/MemoryPool.cpp
    ai/onnx/ONNXInferenceEngine.cpp
    ai/onnx/ONNXModelLoader.cpp
    ai/onnx/ONNXPlugin.cpp
    ai/onnx/Tensor.cpp
    npc/AIMemory.cpp
    npc/NPCBrain.cpp
    npc/NPCPersonality.cpp
    gameplay/DifficultyController.cpp
    gameplay/PlayerModel.cpp
    narrative/StoryGraph.cpp
    narrative/StoryParser.cpp
    asset/AssetGenerator.cpp
    audio/VoiceSynthesis.cpp
    storyboard/Storyboard.cpp
    video/VideoCompositor.cpp
    neural/NeuralAmbientOcclusion.cpp
    neural/NeuralAntiAlias.cpp
    neural/NeuralUpscaleEffect.cpp
    ui/WorkflowCanvas.cpp
    workflow/WorkflowFactory.cpp
    workflow/WorkflowGraph.cpp
    workflow/nodes/AIGenerationNodes.cpp
    editor/AIEditorPanel.cpp
    editor/AssetBrowser.cpp
    editor/AssetGeneratorPanel.cpp
    editor/BehaviorTreeEditor.cpp
    editor/SceneEditor.cpp
    team/TeamAgent.cpp
    team/TeamDirector.cpp
    team/TeamLead.cpp
    team/TeamSpecialist.cpp
    team/TeamOrchestrator.cpp
    team/QualityGate.cpp
    team/WorkflowManager.cpp
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
