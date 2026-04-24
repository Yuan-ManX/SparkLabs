#ifndef SPARKLABS_GAME_SPARKCRAFT_H
#define SPARKLABS_GAME_SPARKCRAFT_H

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>
#include "../../core/math/Vector3.h"

namespace SparkLabs {
namespace sparkai {

// Game engine template types
enum class GameEngineType {
    Canvas2D,
    Phaser,
    ThreeJS,
    WebGL,
    Custom
};

// Game genre types
enum class GameGenre {
    Platformer,
    Action,
    RPG,
    Strategy,
    Puzzle,
    Shooter,
    Adventure,
    CardGame,
    TowerDefense,
    Survival,
    Custom
};

// Template metadata
struct TemplateMetadata {
    std::string id;
    std::string name;
    std::string description;
    GameEngineType engineType;
    GameGenre genre;
    int version;
    std::vector<std::string> tags;
    bool isVerified;
    int successRate;
};

// File template entry
struct FileTemplate {
    std::string path;
    std::string contentTemplate;
    bool isMainFile;
    std::map<std::string, std::string> variables;
};

// SparkCraft Template - A reusable game project skeleton
class SparkCraftTemplate {
public:
    SparkCraftTemplate(const TemplateMetadata& metadata);
    ~SparkCraftTemplate() = default;

    // Template management
    void AddFileTemplate(const FileTemplate& file);
    void RemoveFileTemplate(const std::string& path);
    
    // Template generation
    std::vector<FileTemplate> GenerateProjectFiles(
        const std::string& gameName,
        const std::string& description,
        const std::map<std::string, std::string>& customVariables
    );
    
    // Template learning
    void RecordSuccess(bool success);
    void AddTag(const std::string& tag);
    
    // Getters
    const TemplateMetadata& GetMetadata() const { return metadata; }
    const std::vector<FileTemplate>& GetFileTemplates() const { return files; }

private:
    TemplateMetadata metadata;
    std::vector<FileTemplate> files;
    int totalAttempts;
    int successfulAttempts;
};

// SparkCraft System - Manages template library and generation
class SparkCraftSystem {
public:
    SparkCraftSystem();
    ~SparkCraftSystem() = default;

    // Template registration
    void RegisterTemplate(std::unique_ptr<SparkCraftTemplate> aTemplate);
    void UnregisterTemplate(const std::string& templateId);

    // Template discovery
    std::vector<SparkCraftTemplate*> FindTemplatesByGenre(GameGenre genre);
    std::vector<SparkCraftTemplate*> FindTemplatesByEngine(GameEngineType engine);
    SparkCraftTemplate* FindBestTemplate(const std::string& prompt);
    
    // Project generation
    struct GenerationResult {
        bool success;
        std::vector<FileTemplate> generatedFiles;
        std::string selectedTemplate;
        std::vector<std::string> warnings;
        std::vector<std::string> suggestions;
    };
    
    GenerationResult GenerateGame(
        const std::string& prompt,
        const std::string& gameName,
        const std::map<std::string, std::string>& options
    );

    // Template learning
    void UpdateTemplatePerformance(const std::string& templateId, bool success);
    void LearnFromProject(const std::string& templateId, const std::vector<FileTemplate>& projectFiles);

    // Get all templates
    const std::map<std::string, std::unique_ptr<SparkCraftTemplate>>& GetTemplates() const { return templates; }

private:
    std::map<std::string, std::unique_ptr<SparkCraftTemplate>> templates;
    std::map<std::string, std::vector<std::string>> promptToTemplateCache;
    
    void InitializeDefaultTemplates();
    std::string AnalyzePrompt(const std::string& prompt);
    SparkCraftTemplate* SelectOptimalTemplate(const std::string& analysis, GameGenre genre);
};

} // namespace sparkai
} // namespace SparkLabs

#endif // SPARKLABS_GAME_SPARKCRAFT_H
