#include "AssetGeneratorPanel.h"

namespace SparkLabs {

AssetGeneratorPanel::AssetGeneratorPanel()
    : m_IsGenerating(false)
    , m_Progress(0.0f) {
}

AssetGeneratorPanel::~AssetGeneratorPanel() {
}

void AssetGeneratorPanel::ShowGenerator(const String& assetType) {
    m_AssetType = assetType;
}

void AssetGeneratorPanel::SetPrompt(const String& prompt) {
    m_Prompt = prompt;
}

void AssetGeneratorPanel::SetGenerationOptions(const GenerationOptions& options) {
    m_Options = options;
}

void AssetGeneratorPanel::Generate() {
    if (m_IsGenerating) {
        return;
    }

    if (m_Prompt.Empty()) {
        OnGenerationFailed.Emit();
        return;
    }

    m_IsGenerating = true;
    m_Progress = 0.0f;
}

void AssetGeneratorPanel::CancelGeneration() {
    if (m_IsGenerating) {
        m_IsGenerating = false;
        m_Progress = 0.0f;
    }
}

void AssetGeneratorPanel::Update(float32 deltaTime) {
    if (m_IsGenerating) {
        m_Progress += deltaTime * 0.5f;
        if (m_Progress >= 1.0f) {
            m_Progress = 1.0f;
            m_IsGenerating = false;
            OnGenerationComplete.Emit();
        }
    }
}

void AssetGeneratorPanel::Render() {
}

}
