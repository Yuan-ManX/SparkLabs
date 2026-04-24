#ifndef SPARKLABS_GAME_SPARKDEBUG_H
#define SPARKLABS_GAME_SPARKDEBUG_H

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>

namespace SparkLabs {
namespace sparkai {

enum class DebugIssueType {
    SyntaxError,
    RuntimeError,
    LogicError,
    PerformanceIssue,
    AssetError,
    IntegrationError
};

enum class Severity {
    Critical,
    High,
    Medium,
    Low,
    Info
};

struct DebugIssue {
    DebugIssueType type;
    Severity severity;
    std::string message;
    std::string file;
    int line;
    int column;
    std::string suggestion;
    bool fixed;
};

struct FixPattern {
    std::string id;
    std::string name;
    std::string description;
    std::string problemPattern;
    std::string fixPattern;
    DebugIssueType appliesTo;
    int successCount;
    int useCount;
};

class SparkDebugger {
public:
    SparkDebugger();
    ~SparkDebugger() = default;
    
    // File validation
    std::vector<DebugIssue> ValidateFile(const std::string& filePath, const std::string& content);
    std::vector<DebugIssue> ValidateJavaScript(const std::string& content);
    std::vector<DebugIssue> ValidateHTML(const std::string& content);
    std::vector<DebugIssue> ValidateCSS(const std::string& content);
    
    // Game validation
    std::vector<DebugIssue> ValidateGameProject(const std::map<std::string, std::string>& files);
    
    // Automatic fixing
    bool AutoFixIssue(DebugIssue& issue, std::string& content);
    std::string ApplyFix(const std::string& content, const FixPattern& pattern);
    
    // Pattern management
    void AddFixPattern(const FixPattern& pattern);
    void RemoveFixPattern(const std::string& id);
    void UpdatePatternSuccess(const std::string& id, bool success);
    
    // Playability testing
    struct PlayabilityReport {
        bool canLoad;
        bool hasCanvas;
        bool hasGameLoop;
        bool respondsToInput;
        std::vector<std::string> consoleErrors;
        std::vector<std::string> warnings;
        std::vector<std::string> suggestions;
        float overallScore;
    };
    
    PlayabilityReport CheckPlayability(const std::string& htmlPath);
    
    // Code quality
    struct QualityReport {
        float readabilityScore;
        float maintainabilityScore;
        float performanceScore;
        std::vector<std::string> improvementSuggestions;
    };
    
    QualityReport AnalyzeCodeQuality(const std::string& content);
    
private:
    std::vector<FixPattern> patterns;
    std::map<std::string, int> patternIndex;
    
    void InitializeBuiltinPatterns();
    FixPattern* FindBestPattern(const DebugIssue& issue);
    
    // Specific issue detection
    std::vector<DebugIssue> CheckMissingElements(const std::string& content);
    std::vector<DebugIssue> CheckUndefinedVariables(const std::string& content);
    std::vector<DebugIssue> CheckLoopIssues(const std::string& content);
    std::vector<DebugIssue> CheckPerformanceIssues(const std::string& content);
    std::vector<DebugIssue> CheckGameStructure(const std::string& content);
};

class SparkBenchmark {
public:
    SparkBenchmark();
    ~SparkBenchmark() = default;
    
    // Comprehensive game evaluation
    struct EvaluationReport {
        // Build health
        bool buildsSuccessfully;
        int compileErrors;
        int compileWarnings;
        
        // Visual usability
        float layoutScore;
        float colorSchemeScore;
        float typographyScore;
        
        // Intent alignment
        float featureCompleteness;
        float gameplayFunFactor;
        float userExperience;
        
        // Overall score
        float totalScore;
        std::string letterGrade;
        
        std::vector<std::string> recommendations;
        std::vector<std::string> standoutFeatures;
    };
    
    EvaluationReport EvaluateGame(const std::map<std::string, std::string>& files, const std::string& prompt);
    
    // Individual category evaluations
    float EvaluateBuildHealth(const std::map<std::string, std::string>& files);
    float EvaluateVisualUsability(const std::string& htmlContent);
    float EvaluateIntentAlignment(const std::map<std::string, std::string>& files, const std::string& prompt);
    
    // AI-based testing
    struct TestCase {
        std::string name;
        std::string description;
        std::function<bool()> testFunction;
        bool passed;
    };
    
    std::vector<TestCase> GenerateTestCases(const std::string& prompt);
    bool RunAIGameTest(const std::string& testDescription);
    
private:
    std::string CalculateLetterGrade(float score);
};

} // namespace sparkai
} // namespace SparkLabs

#endif // SPARKLABS_GAME_SPARKDEBUG_H
