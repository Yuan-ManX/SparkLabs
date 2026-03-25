#ifndef SPARKLABS_SPARKAI_ASSET_ASSETGENERATOR_H
#define SPARKLABS_SPARKAI_ASSET_ASSETGENERATOR_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "../../core/Map.h"
#include "../../core/Variant.h"
#include "../../core/math/Vector3.h"
#include "../../core/math/Vector2.h"

namespace SparkLabs {

enum class AssetType {
    Character,
    Environment,
    Prop,
    Texture,
    Material,
    Mesh,
    Audio,
    Animation
};

struct GenerationPrompt {
    String description;
    String style;
    String negativePrompt;
    int32 width;
    int32 height;
    int32 steps;
    float32 guidanceScale;
    uint64 seed;
    Map<StringHash, Variant> parameters;

    GenerationPrompt()
        : width(512)
        , height(512)
        , steps(30)
        , guidanceScale(7.5f)
        , seed(0)
    {}
};

struct GeneratedAsset {
    StringHash id;
    String name;
    AssetType type;
    String filePath;
    Vector<uint8> data;
    int32 width;
    int32 height;
    Map<StringHash, Variant> metadata;
    GenerationPrompt prompt;

    GeneratedAsset() : id(StringHash()), type(AssetType::Prop), width(0), height(0) {}
};

struct CharacterGenerationRequest {
    String name;
    String description;
    String personality;
    String appearance;
    String artStyle;
    Vector3 colorScheme;
    Vector<String> tags;
    GenerationPrompt basePrompt;

    CharacterGenerationRequest() : colorScheme(Vector3(1.0f, 1.0f, 1.0f)) {}
};

struct EnvironmentGenerationRequest {
    String name;
    String location;
    String description;
    String timeOfDay;
    String weather;
    String artStyle;
    Vector2 size;
    Vector<String> tags;
    GenerationPrompt basePrompt;

    EnvironmentGenerationRequest() : size(Vector2(1024.0f, 1024.0f)) {}
};

class AssetGenerator {
public:
    AssetGenerator();
    ~AssetGenerator();

    GeneratedAsset GenerateCharacter(const CharacterGenerationRequest& request);
    GeneratedAsset GenerateEnvironment(const EnvironmentGenerationRequest& request);
    GeneratedAsset GenerateFromPrompt(const GenerationPrompt& prompt, AssetType type);

    void SetOutputDirectory(const String& path) { m_OutputDirectory = path; }
    const String& GetOutputDirectory() const { return m_OutputDirectory; }

    void SetStylePreset(const String& preset);
    void AddStyleKeyword(const String& keyword);
    void ClearStyleKeywords();

    bool SaveAsset(const GeneratedAsset& asset, const String& filePath);
    GeneratedAsset LoadAsset(const String& filePath);

    Vector<GeneratedAsset> GenerateBatch(const Vector<GenerationPrompt>& prompts);

private:
    String GenerateCharacterPrompt(const CharacterGenerationRequest& request);
    String GenerateEnvironmentPrompt(const EnvironmentGenerationRequest& request);
    GeneratedAsset CreatePlaceholderAsset(const String& name, AssetType type);
    StringHash GenerateUniqueId();

    String m_OutputDirectory;
    Vector<String> m_StyleKeywords;
    String m_CurrentStylePreset;
    uint64 m_IdCounter;
};

}

#endif
