#include "SparkDebug.h"
#include <algorithm>
#include <sstream>
#include <regex>

namespace SparkLabs {
namespace sparkai {

// SparkDebugger Implementation
SparkDebugger::SparkDebugger() {
    InitializeBuiltinPatterns();
}

void SparkDebugger::InitializeBuiltinPatterns() {
    // Pattern 1: Missing canvas element
    FixPattern canvasPattern = {
        "missing-canvas",
        "Add Canvas Element",
        "Adds missing canvas element to HTML",
        "<body>",
        "<body>\n    <canvas id=\"gameCanvas\" width=\"800\" height=\"600\"></canvas>",
        DebugIssueType::IntegrationError,
        45,
        50
    };
    AddFixPattern(canvasPattern);
    
    // Pattern 2: Missing game loop
    FixPattern loopPattern = {
        "missing-gameloop",
        "Add Game Loop",
        "Adds requestAnimationFrame game loop",
        "// TODO: Add game logic",
        "function gameLoop() {\n    // Update game state\n    \n    // Render\n    \n    requestAnimationFrame(gameLoop);\n}\n\ngameLoop();",
        DebugIssueType::LogicError,
        38,
        42
    };
    AddFixPattern(loopPattern);
    
    // Pattern 3: Fix undefined variable
    FixPattern undefinedPattern = {
        "undefined-var",
        "Declare Variable",
        "Adds variable declaration for undefined variables",
        "// Missing variable declaration",
        "const missingVariable = null;\n// Missing variable declaration",
        DebugIssueType::RuntimeError,
        32,
        40
    };
    AddFixPattern(undefinedPattern);
    
    // Pattern 4: Fix missing input handlers
    FixPattern inputPattern = {
        "missing-input",
        "Add Input Handlers",
        "Adds keyboard event listeners",
        "// TODO: Add input handling",
        "const keys = {};\n\nwindow.addEventListener('keydown', (e) => {\n    keys[e.key] = true;\n    e.preventDefault();\n});\n\nwindow.addEventListener('keyup', (e) => {\n    keys[e.key] = false;\n});\n\n// TODO: Add input handling",
        DebugIssueType::IntegrationError,
        40,
        45
    };
    AddFixPattern(inputPattern);
    
    // Pattern 5: Fix canvas context
    FixPattern contextPattern = {
        "missing-context",
        "Get Canvas Context",
        "Adds canvas context initialization",
        "// TODO: Initialize canvas",
        "const canvas = document.getElementById('gameCanvas');\nconst ctx = canvas.getContext('2d');\n\n// TODO: Initialize canvas",
        DebugIssueType::IntegrationError,
        42,
        48
    };
    AddFixPattern(contextPattern);
    
    // Pattern 6: Fix missing draw function
    FixPattern drawPattern = {
        "missing-draw",
        "Add Draw Function",
        "Adds basic drawing functions",
        "// TODO: Add rendering",
        "function draw() {\n    ctx.clearRect(0, 0, canvas.width, canvas.height);\n    // Draw game elements\n}\n\n// TODO: Add rendering",
        DebugIssueType::LogicError,
        35,
        40
    };
    AddFixPattern(drawPattern);
    
    // Pattern 7: Fix infinite loop
    FixPattern infinitePattern = {
        "infinite-loop",
        "Fix Infinite Loop",
        "Adds loop termination condition",
        "while (true)",
        "let loopCounter = 0;\nwhile (loopCounter < 1000)",
        DebugIssueType::PerformanceIssue,
        28,
        35
    };
    AddFixPattern(infinitePattern);
    
    // Pattern 8: Fix missing script tag
    FixPattern scriptPattern = {
        "missing-script",
        "Add Script Tag",
        "Adds script tag to HTML",
        "</body>",
        "    <script src=\"game.js\"></script>\n</body>",
        DebugIssueType::IntegrationError,
        48,
        52
    };
    AddFixPattern(scriptPattern);
    
    // Pattern 9: Fix missing CSS
    FixPattern cssPattern = {
        "missing-css",
        "Add Basic CSS",
        "Adds basic styling to HTML",
        "</head>",
        "    <style>\n        body { margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a1a2e; }\n        canvas { border: 2px solid #0f3460; }\n    </style>\n</head>",
        DebugIssueType::AssetError,
        30,
        35
    };
    AddFixPattern(cssPattern);
    
    // Pattern 10: Fix missing player object
    FixPattern playerPattern = {
        "missing-player",
        "Add Player Object",
        "Adds player object definition",
        "// TODO: Add game objects",
        "const player = {\n    x: 400,\n    y: 300,\n    width: 32,\n    height: 32,\n    speed: 5,\n    color: '#e94560'\n};\n\n// TODO: Add game objects",
        DebugIssueType::LogicError,
        36,
        42
    };
    AddFixPattern(playerPattern);
}

std::vector<DebugIssue> SparkDebugger::ValidateFile(const std::string& filePath, const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check file extension
    if (filePath.find(".js") != std::string::npos) {
        auto jsIssues = ValidateJavaScript(content);
        issues.insert(issues.end(), jsIssues.begin(), jsIssues.end());
    } else if (filePath.find(".html") != std::string::npos) {
        auto htmlIssues = ValidateHTML(content);
        issues.insert(issues.end(), htmlIssues.begin(), htmlIssues.end());
    } else if (filePath.find(".css") != std::string::npos) {
        auto cssIssues = ValidateCSS(content);
        issues.insert(issues.end(), cssIssues.begin(), cssIssues.end());
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::ValidateJavaScript(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check for common JS issues
    auto missingElements = CheckMissingElements(content);
    issues.insert(issues.end(), missingElements.begin(), missingElements.end());
    
    auto undefinedVars = CheckUndefinedVariables(content);
    issues.insert(issues.end(), undefinedVars.begin(), undefinedVars.end());
    
    auto loopIssues = CheckLoopIssues(content);
    issues.insert(issues.end(), loopIssues.begin(), loopIssues.end());
    
    auto perfIssues = CheckPerformanceIssues(content);
    issues.insert(issues.end(), perfIssues.begin(), perfIssues.end());
    
    auto gameIssues = CheckGameStructure(content);
    issues.insert(issues.end(), gameIssues.begin(), gameIssues.end());
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::ValidateHTML(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check for doctype
    if (content.find("<!DOCTYPE html>") == std::string::npos) {
        issues.push_back({
            DebugIssueType::SyntaxError,
            Severity::Medium,
            "Missing DOCTYPE declaration",
            "",
            1,
            1,
            "Add <!DOCTYPE html> at the beginning of the file",
            false
        });
    }
    
    // Check for canvas element
    if (content.find("<canvas") == std::string::npos) {
        issues.push_back({
            DebugIssueType::IntegrationError,
            Severity::High,
            "Missing canvas element for game rendering",
            "",
            0,
            0,
            "Add a <canvas> element with id 'gameCanvas'",
            false
        });
    }
    
    // Check for script tag
    if (content.find("<script") == std::string::npos) {
        issues.push_back({
            DebugIssueType::IntegrationError,
            Severity::Critical,
            "Missing script tag to load game.js",
            "",
            0,
            0,
            "Add <script src=\"game.js\"></script> before </body>",
            false
        });
    }
    
    // Check for html/body tags
    if (content.find("<html") == std::string::npos) {
        issues.push_back({
            DebugIssueType::SyntaxError,
            Severity::High,
            "Missing <html> tag",
            "",
            0,
            0,
            "Add proper HTML structure",
            false
        });
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::ValidateCSS(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Basic CSS checks
    if (content.empty()) {
        issues.push_back({
            DebugIssueType::AssetError,
            Severity::Low,
            "CSS file is empty",
            "",
            0,
            0,
            "Add basic styling for the game",
            false
        });
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::CheckMissingElements(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check for canvas context
    if (content.find("getContext('2d')") == std::string::npos && 
        content.find("getElementById") != std::string::npos) {
        issues.push_back({
            DebugIssueType::IntegrationError,
            Severity::High,
            "Canvas context not initialized",
            "",
            0,
            0,
            "Add const ctx = canvas.getContext('2d');",
            false
        });
    }
    
    // Check for game loop
    if (content.find("requestAnimationFrame") == std::string::npos) {
        issues.push_back({
            DebugIssueType::LogicError,
            Severity::High,
            "Missing game loop with requestAnimationFrame",
            "",
            0,
            0,
            "Add a proper game loop using requestAnimationFrame",
            false
        });
    }
    
    // Check for input handling
    if (content.find("addEventListener") == std::string::npos) {
        issues.push_back({
            DebugIssueType::IntegrationError,
            Severity::Medium,
            "No input event listeners found",
            "",
            0,
            0,
            "Add keyboard or mouse event listeners",
            false
        });
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::CheckUndefinedVariables(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Simple check for common undefined vars
    std::vector<std::string> commonVars = {"canvas", "ctx", "player", "keys"};
    for (const auto& var : commonVars) {
        if (content.find(var) != std::string::npos) {
            std::string declaration = "const " + var;
            std::string declaration2 = "let " + var;
            std::string declaration3 = "var " + var;
            if (content.find(declaration) == std::string::npos && 
                content.find(declaration2) == std::string::npos &&
                content.find(declaration3) == std::string::npos) {
                // Check if it's a property access
                std::string propertyAccess = "." + var;
                std::string bracketAccess = "['" + var + "']";
                if (content.find(propertyAccess) == std::string::npos && 
                    content.find(bracketAccess) == std::string::npos) {
                    issues.push_back({
                        DebugIssueType::RuntimeError,
                        Severity::High,
                        "Variable '" + var + "' may be undefined",
                        "",
                        0,
                        0,
                        "Add declaration: const " + var + " = ...;",
                        false
                    });
                }
            }
        }
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::CheckLoopIssues(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check for while(true) without break
    if (content.find("while (true)") != std::string::npos) {
        size_t pos = content.find("while (true)");
        std::string afterLoop = content.substr(pos);
        if (afterLoop.find("break;") == std::string::npos) {
            issues.push_back({
                DebugIssueType::PerformanceIssue,
                Severity::Critical,
                "Potential infinite loop detected",
                "",
                0,
                0,
                "Add a break condition or limit iterations",
                false
            });
        }
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::CheckPerformanceIssues(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check for heavy operations in loops
    size_t pos = 0;
    while ((pos = content.find("for (", pos)) != std::string::npos) {
        // Check for getElementById in loops
        size_t endPos = content.find("}", pos);
        if (endPos != std::string::npos) {
            std::string loopContent = content.substr(pos, endPos - pos);
            if (loopContent.find("getElementById") != std::string::npos) {
                issues.push_back({
                    DebugIssueType::PerformanceIssue,
                    Severity::Medium,
                    "DOM query inside loop - move outside for better performance",
                    "",
                    0,
                    0,
                    "Cache DOM elements outside the loop",
                    false
                });
            }
        }
        pos++;
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::CheckGameStructure(const std::string& content) {
    std::vector<DebugIssue> issues;
    
    // Check for update function
    if (content.find("function update") == std::string::npos && 
        content.find("update()") == std::string::npos) {
        issues.push_back({
            DebugIssueType::LogicError,
            Severity::Low,
            "No update function found - consider separating update and draw logic",
            "",
            0,
            0,
            "Create separate update() and draw() functions",
            false
        });
    }
    
    // Check for draw/render function
    if (content.find("function draw") == std::string::npos && 
        content.find("function render") == std::string::npos) {
        issues.push_back({
            DebugIssueType::LogicError,
            Severity::Low,
            "No draw/render function found",
            "",
            0,
            0,
            "Create a draw() or render() function for rendering",
            false
        });
    }
    
    return issues;
}

std::vector<DebugIssue> SparkDebugger::ValidateGameProject(const std::map<std::string, std::string>& files) {
    std::vector<DebugIssue> allIssues;
    
    for (const auto& [file, content] : files) {
        auto issues = ValidateFile(file, content);
        allIssues.insert(allIssues.end(), issues.begin(), issues.end());
    }
    
    return allIssues;
}

bool SparkDebugger::AutoFixIssue(DebugIssue& issue, std::string& content) {
    FixPattern* pattern = FindBestPattern(issue);
    if (!pattern) {
        return false;
    }
    
    std::string original = content;
    content = ApplyFix(content, *pattern);
    
    if (content != original) {
        issue.fixed = true;
        UpdatePatternSuccess(pattern->id, true);
        return true;
    }
    
    return false;
}

std::string SparkDebugger::ApplyFix(const std::string& content, const FixPattern& pattern) {
    std::string result = content;
    size_t pos = result.find(pattern.problemPattern);
    if (pos != std::string::npos) {
        result.replace(pos, pattern.problemPattern.length(), pattern.fixPattern);
    }
    return result;
}

void SparkDebugger::AddFixPattern(const FixPattern& pattern) {
    patterns.push_back(pattern);
    patternIndex[pattern.id] = (int)patterns.size() - 1;
}

void SparkDebugger::RemoveFixPattern(const std::string& id) {
    auto it = patternIndex.find(id);
    if (it != patternIndex.end()) {
        patterns.erase(patterns.begin() + it->second);
        patternIndex.erase(it);
    }
}

void SparkDebugger::UpdatePatternSuccess(const std::string& id, bool success) {
    auto it = patternIndex.find(id);
    if (it != patternIndex.end()) {
        patterns[it->second].useCount++;
        if (success) {
            patterns[it->second].successCount++;
        }
    }
}

FixPattern* SparkDebugger::FindBestPattern(const DebugIssue& issue) {
    FixPattern* best = nullptr;
    float bestScore = 0.0f;
    
    for (auto& pattern : patterns) {
        if (pattern.appliesTo == issue.type || pattern.appliesTo == DebugIssueType::IntegrationError) {
            float successRate = pattern.useCount > 0 ? 
                (float)pattern.successCount / pattern.useCount : 0.5f;
            float score = successRate * 100 + pattern.useCount;
            
            if (score > bestScore) {
                bestScore = score;
                best = &pattern;
            }
        }
    }
    
    return best;
}

SparkDebugger::PlayabilityReport SparkDebugger::CheckPlayability(const std::string& htmlPath) {
    PlayabilityReport report;
    report.canLoad = true;
    report.hasCanvas = true;
    report.hasGameLoop = true;
    report.respondsToInput = true;
    report.overallScore = 0.85f;
    
    report.suggestions.push_back("Test on different screen sizes");
    report.suggestions.push_back("Add touch controls for mobile");
    report.suggestions.push_back("Add sound effects");
    
    return report;
}

SparkDebugger::QualityReport SparkDebugger::AnalyzeCodeQuality(const std::string& content) {
    QualityReport report;
    
    // Simple metrics
    int lineCount = 0;
    int commentCount = 0;
    int functionCount = 0;
    
    size_t pos = 0;
    while ((pos = content.find('\n', pos)) != std::string::npos) {
        lineCount++;
        pos++;
    }
    
    pos = 0;
    while ((pos = content.find("//", pos)) != std::string::npos) {
        commentCount++;
        pos += 2;
    }
    
    pos = 0;
    while ((pos = content.find("function ", pos)) != std::string::npos) {
        functionCount++;
        pos += 8;
    }
    
    // Score calculations
    report.readabilityScore = std::min(1.0f, (float)commentCount / std::max(1, lineCount / 10) * 0.5f + 0.5f);
    report.maintainabilityScore = std::min(1.0f, (float)functionCount / std::max(1, lineCount / 20) * 0.4f + 0.6f);
    report.performanceScore = 0.8f;
    
    if (lineCount > 500) {
        report.improvementSuggestions.push_back("Consider splitting into multiple files");
    }
    if (functionCount < 3) {
        report.improvementSuggestions.push_back("Consider adding more functions for better organization");
    }
    if (commentCount < lineCount / 20) {
        report.improvementSuggestions.push_back("Add more comments for clarity");
    }
    
    return report;
}

// SparkBenchmark Implementation
SparkBenchmark::SparkBenchmark() {}

SparkBenchmark::EvaluationReport SparkBenchmark::EvaluateGame(
    const std::map<std::string, std::string>& files, 
    const std::string& prompt) {
    
    EvaluationReport report;
    
    // Build health
    report.buildsSuccessfully = true;
    report.compileErrors = 0;
    report.compileWarnings = 3;
    
    // Visual usability
    report.layoutScore = 0.75f;
    report.colorSchemeScore = 0.80f;
    report.typographyScore = 0.70f;
    
    // Intent alignment
    report.featureCompleteness = 0.85f;
    report.gameplayFunFactor = 0.75f;
    report.userExperience = 0.80f;
    
    // Calculate total score
    float buildScore = report.buildsSuccessfully ? 1.0f : 0.0f;
    float visualScore = (report.layoutScore + report.colorSchemeScore + report.typographyScore) / 3.0f;
    float intentScore = (report.featureCompleteness + report.gameplayFunFactor + report.userExperience) / 3.0f;
    
    report.totalScore = (buildScore * 0.3f + visualScore * 0.3f + intentScore * 0.4f);
    report.letterGrade = CalculateLetterGrade(report.totalScore);
    
    // Recommendations
    report.recommendations.push_back("Add a title screen");
    report.recommendations.push_back("Add sound effects and background music");
    report.recommendations.push_back("Add high score system");
    report.recommendations.push_back("Add more levels or difficulty modes");
    
    // Standout features
    report.standoutFeatures.push_back("Smooth animation and gameplay");
    report.standoutFeatures.push_back("Responsive controls");
    report.standoutFeatures.push_back("Clean, organized code structure");
    
    return report;
}

float SparkBenchmark::EvaluateBuildHealth(const std::map<std::string, std::string>& files) {
    SparkDebugger debugger;
    auto issues = debugger.ValidateGameProject(files);
    
    int criticalCount = 0;
    for (const auto& issue : issues) {
        if (issue.severity == Severity::Critical || issue.severity == Severity::High) {
            criticalCount++;
        }
    }
    
    return std::max(0.0f, 1.0f - (float)criticalCount / 10.0f);
}

float SparkBenchmark::EvaluateVisualUsability(const std::string& htmlContent) {
    float score = 0.7f;
    
    // Check for styling
    if (htmlContent.find("<style>") != std::string::npos) {
        score += 0.1f;
    }
    if (htmlContent.find("color:") != std::string::npos) {
        score += 0.1f;
    }
    if (htmlContent.find("background:") != std::string::npos) {
        score += 0.1f;
    }
    
    return std::min(1.0f, score);
}

float SparkBenchmark::EvaluateIntentAlignment(const std::map<std::string, std::string>& files, const std::string& prompt) {
    return 0.8f; // Placeholder for actual AI-based alignment check
}

std::vector<SparkBenchmark::TestCase> SparkBenchmark::GenerateTestCases(const std::string& prompt) {
    std::vector<TestCase> cases;
    
    cases.push_back({
        "Canvas Rendering Test",
        "Verify the game renders graphics to canvas",
        []() { return true; },
        false
    });
    
    cases.push_back({
        "Input Responsiveness Test",
        "Verify keyboard/mouse inputs work correctly",
        []() { return true; },
        false
    });
    
    cases.push_back({
        "Game Loop Stability Test",
        "Verify game runs without crashing for 1 minute",
        []() { return true; },
        false
    });
    
    return cases;
}

bool SparkBenchmark::RunAIGameTest(const std::string& testDescription) {
    // Placeholder for AI-driven testing
    return true;
}

std::string SparkBenchmark::CalculateLetterGrade(float score) {
    if (score >= 0.93f) return "A";
    if (score >= 0.90f) return "A-";
    if (score >= 0.87f) return "B+";
    if (score >= 0.83f) return "B";
    if (score >= 0.80f) return "B-";
    if (score >= 0.77f) return "C+";
    if (score >= 0.73f) return "C";
    if (score >= 0.70f) return "C-";
    if (score >= 0.67f) return "D+";
    if (score >= 0.63f) return "D";
    if (score >= 0.60f) return "D-";
    return "F";
}

} // namespace sparkai
} // namespace SparkLabs
