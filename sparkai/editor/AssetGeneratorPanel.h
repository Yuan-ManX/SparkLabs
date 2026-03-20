#pragma once

#include "../core/Types.h"
#include "../core/string/String.h"
#include "../core/Threading/Signal.h"
#include "../core/memory/SmartPtr.h"
#include "../engine/asset/GenerationOptions.h"

namespace SparkLabs {

class AssetGeneratorPanel {
public:
    AssetGeneratorPanel();
    ~AssetGeneratorPanel();

    void ShowGenerator(const String& assetType);
    void SetPrompt(const String& prompt);
    void SetGenerationOptions(const GenerationOptions& options);
    void Generate();
    void CancelGeneration();

    void Update(float32 deltaTime);
    void Render();

    Signal<void> OnGenerationComplete;
    Signal<void> OnGenerationFailed;

    bool IsGenerating() const { return m_IsGenerating; }
    const String& GetPrompt() const { return m_Prompt; }
    const String& GetAssetType() const { return m_AssetType; }
    const GenerationOptions& GetGenerationOptions() const { return m_Options; }

private:
    String m_AssetType;
    String m_Prompt;
    GenerationOptions m_Options;
    bool m_IsGenerating;
    float32 m_Progress;
};

}
