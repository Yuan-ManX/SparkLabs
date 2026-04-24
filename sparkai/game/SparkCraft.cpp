#include "SparkCraft.h"
#include <algorithm>
#include <sstream>

namespace SparkLabs {
namespace sparkai {

// SparkCraftTemplate Implementation
SparkCraftTemplate::SparkCraftTemplate(const TemplateMetadata& meta)
    : metadata(meta), totalAttempts(0), successfulAttempts(0) {
}

void SparkCraftTemplate::AddFileTemplate(const FileTemplate& file) {
    files.push_back(file);
}

void SparkCraftTemplate::RemoveFileTemplate(const std::string& path) {
    files.erase(
        std::remove_if(files.begin(), files.end(),
            [&path](const FileTemplate& f) { return f.path == path; }),
        files.end()
    );
}

std::vector<FileTemplate> SparkCraftTemplate::GenerateProjectFiles(
    const std::string& gameName,
    const std::string& description,
    const std::map<std::string, std::string>& customVariables
) {
    std::vector<FileTemplate> result;
    
    for (const auto& file : files) {
        FileTemplate generated = file;
        std::string content = file.contentTemplate;
        
        // Replace built-in variables
        auto ReplaceVariable = [&](const std::string& var, const std::string& value) {
            std::string placeholder = "{{" + var + "}}";
            size_t pos = 0;
            while ((pos = content.find(placeholder, pos)) != std::string::npos) {
                content.replace(pos, placeholder.length(), value);
                pos += value.length();
            }
        };
        
        ReplaceVariable("GAME_NAME", gameName);
        ReplaceVariable("GAME_DESCRIPTION", description);
        
        // Replace custom variables
        for (const auto& [key, value] : customVariables) {
            ReplaceVariable(key, value);
        }
        
        // Replace file path variables
        std::string path = file.path;
        auto ReplacePathVariable = [&](const std::string& var, const std::string& value) {
            std::string placeholder = "{{" + var + "}}";
            size_t pos = 0;
            while ((pos = path.find(placeholder, pos)) != std::string::npos) {
                path.replace(pos, placeholder.length(), value);
                pos += value.length();
            }
        };
        ReplacePathVariable("GAME_NAME", gameName);
        
        generated.path = path;
        generated.contentTemplate = content;
        result.push_back(generated);
    }
    
    return result;
}

void SparkCraftTemplate::RecordSuccess(bool success) {
    totalAttempts++;
    if (success) {
        successfulAttempts++;
    }
    metadata.successRate = totalAttempts > 0 
        ? (successfulAttempts * 100 / totalAttempts) 
        : 0;
}

void SparkCraftTemplate::AddTag(const std::string& tag) {
    if (std::find(metadata.tags.begin(), metadata.tags.end(), tag) == metadata.tags.end()) {
        metadata.tags.push_back(tag);
    }
}

// SparkCraftSystem Implementation
SparkCraftSystem::SparkCraftSystem() {
    InitializeDefaultTemplates();
}

void SparkCraftSystem::RegisterTemplate(std::unique_ptr<SparkCraftTemplate> aTemplate) {
    templates[aTemplate->GetMetadata().id] = std::move(aTemplate);
}

void SparkCraftSystem::UnregisterTemplate(const std::string& templateId) {
    templates.erase(templateId);
}

std::vector<SparkCraftTemplate*> SparkCraftSystem::FindTemplatesByGenre(GameGenre genre) {
    std::vector<SparkCraftTemplate*> result;
    for (const auto& [id, tpl] : templates) {
        if (tpl->GetMetadata().genre == genre) {
            result.push_back(tpl.get());
        }
    }
    return result;
}

std::vector<SparkCraftTemplate*> SparkCraftSystem::FindTemplatesByEngine(GameEngineType engine) {
    std::vector<SparkCraftTemplate*> result;
    for (const auto& [id, tpl] : templates) {
        if (tpl->GetMetadata().engineType == engine) {
            result.push_back(tpl.get());
        }
    }
    return result;
}

SparkCraftTemplate* SparkCraftSystem::FindBestTemplate(const std::string& prompt) {
    std::string analysis = AnalyzePrompt(prompt);
    
    // Simple heuristic: find genre based on prompt keywords
    GameGenre detectedGenre = GameGenre::Custom;
    
    std::string lowerPrompt = prompt;
    std::transform(lowerPrompt.begin(), lowerPrompt.end(), lowerPrompt.begin(), ::tolower);
    
    if (lowerPrompt.find("platformer") != std::string::npos || 
        lowerPrompt.find("jump") != std::string::npos ||
        lowerPrompt.find("platform") != std::string::npos) {
        detectedGenre = GameGenre::Platformer;
    } else if (lowerPrompt.find("shoot") != std::string::npos || 
               lowerPrompt.find("gun") != std::string::npos ||
               lowerPrompt.find("bullet") != std::string::npos) {
        detectedGenre = GameGenre::Shooter;
    } else if (lowerPrompt.find("rpg") != std::string::npos || 
               lowerPrompt.find("role") != std::string::npos ||
               lowerPrompt.find("character") != std::string::npos) {
        detectedGenre = GameGenre::RPG;
    } else if (lowerPrompt.find("card") != std::string::npos || 
               lowerPrompt.find("deck") != std::string::npos) {
        detectedGenre = GameGenre::CardGame;
    } else if (lowerPrompt.find("tower") != std::string::npos || 
               lowerPrompt.find("defense") != std::string::npos) {
        detectedGenre = GameGenre::TowerDefense;
    } else if (lowerPrompt.find("puzzle") != std::string::npos) {
        detectedGenre = GameGenre::Puzzle;
    } else if (lowerPrompt.find("adventure") != std::string::npos || 
               lowerPrompt.find("explore") != std::string::npos) {
        detectedGenre = GameGenre::Adventure;
    }
    
    return SelectOptimalTemplate(analysis, detectedGenre);
}

SparkCraftSystem::GenerationResult SparkCraftSystem::GenerateGame(
    const std::string& prompt,
    const std::string& gameName,
    const std::map<std::string, std::string>& options
) {
    GenerationResult result;
    result.success = false;
    
    SparkCraftTemplate* bestTemplate = FindBestTemplate(prompt);
    if (!bestTemplate) {
        result.warnings.push_back("No suitable template found, using default");
        // Fallback to first template
        if (!templates.empty()) {
            bestTemplate = templates.begin()->second.get();
        } else {
            result.warnings.push_back("No templates available");
            return result;
        }
    }
    
    result.selectedTemplate = bestTemplate->GetMetadata().id;
    result.generatedFiles = bestTemplate->GenerateProjectFiles(
        gameName,
        prompt,
        options
    );
    result.success = true;
    result.suggestions.push_back("Consider adding more levels");
    result.suggestions.push_back("Test game on different browsers");
    
    return result;
}

void SparkCraftSystem::UpdateTemplatePerformance(const std::string& templateId, bool success) {
    auto it = templates.find(templateId);
    if (it != templates.end()) {
        it->second->RecordSuccess(success);
    }
}

void SparkCraftSystem::LearnFromProject(const std::string& templateId, const std::vector<FileTemplate>& projectFiles) {
    // Learning logic - analyze successful projects and update templates
    auto it = templates.find(templateId);
    if (it != templates.end()) {
        // Could analyze file structure, patterns, etc.
        it->second->RecordSuccess(true);
    }
}

void SparkCraftSystem::InitializeDefaultTemplates() {
    // Default Platformer Template
    TemplateMetadata platformerMeta = {
        "platformer-basic",
        "2D Platformer Starter",
        "A classic 2D platformer game template with player movement and jumping",
        GameEngineType::Canvas2D,
        GameGenre::Platformer,
        1,
        {"platformer", "2d", "jumping", "side-scrolling"},
        true,
        95
    };
    auto platformerTpl = std::make_unique<SparkCraftTemplate>(platformerMeta);
    
    FileTemplate indexHtml = {
        "{{GAME_NAME}}/index.html",
        R"HTML(<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{GAME_NAME}}</title>
    <style>
        body { margin: 0; padding: 0; background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        canvas { border: 2px solid #0f3460; }
    </style>
</head>
<body>
    <canvas id="gameCanvas" width="800" height="600"></canvas>
    <script src="game.js"></script>
</body>
</html>)HTML",
        true,
        {}
    };
    platformerTpl->AddFileTemplate(indexHtml);
    
    FileTemplate gameJs = {
        "{{GAME_NAME}}/game.js",
        R"JS(// {{GAME_NAME}} - {{GAME_DESCRIPTION}}
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const player = {
    x: 100,
    y: 300,
    width: 32,
    height: 32,
    velocityX: 0,
    velocityY: 0,
    speed: 5,
    jumpPower: 12,
    color: '#e94560'
};

const keys = {};
const platforms = [
    { x: 0, y: 550, width: 800, height: 50 },
    { x: 200, y: 450, width: 150, height: 20 },
    { x: 450, y: 350, width: 150, height: 20 },
    { x: 100, y: 250, width: 150, height: 20 }
];

function applyGravity() {
    player.velocityY += 0.5;
}

function updatePlayer() {
    if (keys['ArrowLeft'] || keys['a']) player.velocityX = -player.speed;
    else if (keys['ArrowRight'] || keys['d']) player.velocityX = player.speed;
    else player.velocityX = 0;
    
    if ((keys['ArrowUp'] || keys['w'] || keys[' ']) && player.y >= canvas.height - player.height - 50) {
        player.velocityY = -player.jumpPower;
    }
    
    applyGravity();
    player.x += player.velocityX;
    player.y += player.velocityY;
    
    platforms.forEach(platform => {
        if (player.x < platform.x + platform.width &&
            player.x + player.width > platform.x &&
            player.y < platform.y + platform.height &&
            player.y + player.height > platform.y) {
            if (player.velocityY > 0) {
                player.y = platform.y - player.height;
                player.velocityY = 0;
            }
        }
    });
    
    if (player.x < 0) player.x = 0;
    if (player.x + player.width > canvas.width) player.x = canvas.width - player.width;
    if (player.y + player.height > canvas.height) {
        player.y = canvas.height - player.height;
        player.velocityY = 0;
    }
}

function drawPlayer() {
    ctx.fillStyle = player.color;
    ctx.fillRect(player.x, player.y, player.width, player.height);
}

function drawPlatforms() {
    ctx.fillStyle = '#0f3460';
    platforms.forEach(p => {
        ctx.fillRect(p.x, p.y, p.width, p.height);
    });
}

function drawBackground() {
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function gameLoop() {
    drawBackground();
    updatePlayer();
    drawPlatforms();
    drawPlayer();
    requestAnimationFrame(gameLoop);
}

window.addEventListener('keydown', (e) => {
    keys[e.key] = true;
    e.preventDefault();
});
window.addEventListener('keyup', (e) => {
    keys[e.key] = false;
});

gameLoop();)JS",
        true,
        {}
    };
    platformerTpl->AddFileTemplate(gameJs);
    
    RegisterTemplate(std::move(platformerTpl));
    
    // Default Shooter Template
    TemplateMetadata shooterMeta = {
        "shooter-basic",
        "Top-Down Shooter Starter",
        "A top-down shooter with player movement and bullet shooting",
        GameEngineType::Canvas2D,
        GameGenre::Shooter,
        1,
        {"shooter", "2d", "top-down", "bullets"},
        true,
        90
    };
    auto shooterTpl = std::make_unique<SparkCraftTemplate>(shooterMeta);
    
    FileTemplate shooterHtml = {
        "{{GAME_NAME}}/index.html",
        R"HTML(<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{GAME_NAME}}</title>
    <style>
        body { margin: 0; padding: 0; background: #16213e; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        canvas { border: 2px solid #0f3460; }
    </style>
</head>
<body>
    <canvas id="gameCanvas" width="800" height="600"></canvas>
    <script src="game.js"></script>
</body>
</html>)HTML",
        true,
        {}
    };
    shooterTpl->AddFileTemplate(shooterHtml);
    
    FileTemplate shooterJs = {
        "{{GAME_NAME}}/game.js",
        R"JS(// {{GAME_NAME}} - {{GAME_DESCRIPTION}}
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const player = {
    x: 400,
    y: 300,
    radius: 15,
    speed: 4,
    color: '#e94560'
};

const bullets = [];
const enemies = [];
const keys = {};

function spawnEnemy() {
    const side = Math.floor(Math.random() * 4);
    let x, y;
    switch(side) {
        case 0: x = Math.random() * canvas.width; y = -20; break;
        case 1: x = canvas.width + 20; y = Math.random() * canvas.height; break;
        case 2: x = Math.random() * canvas.width; y = canvas.height + 20; break;
        case 3: x = -20; y = Math.random() * canvas.height; break;
    }
    enemies.push({
        x, y,
        radius: 12,
        speed: 2,
        color: '#533483'
    });
}

function updatePlayer() {
    if (keys['w'] || keys['ArrowUp']) player.y -= player.speed;
    if (keys['s'] || keys['ArrowDown']) player.y += player.speed;
    if (keys['a'] || keys['ArrowLeft']) player.x -= player.speed;
    if (keys['d'] || keys['ArrowRight']) player.x += player.speed;
    
    player.x = Math.max(player.radius, Math.min(canvas.width - player.radius, player.x));
    player.y = Math.max(player.radius, Math.min(canvas.height - player.radius, player.y));
}

function shoot(x, y) {
    const angle = Math.atan2(y - player.y, x - player.x);
    bullets.push({
        x: player.x,
        y: player.y,
        velocityX: Math.cos(angle) * 8,
        velocityY: Math.sin(angle) * 8,
        radius: 4,
        color: '#f9c74f'
    });
}

function updateBullets() {
    for (let i = bullets.length - 1; i >= 0; i--) {
        bullets[i].x += bullets[i].velocityX;
        bullets[i].y += bullets[i].velocityY;
        if (bullets[i].x < 0 || bullets[i].x > canvas.width || 
            bullets[i].y < 0 || bullets[i].y > canvas.height) {
            bullets.splice(i, 1);
        }
    }
}

function updateEnemies() {
    for (let enemy of enemies) {
        const angle = Math.atan2(player.y - enemy.y, player.x - enemy.x);
        enemy.x += Math.cos(angle) * enemy.speed;
        enemy.y += Math.sin(angle) * enemy.speed;
    }
}

function checkCollisions() {
    for (let i = bullets.length - 1; i >= 0; i--) {
        for (let j = enemies.length - 1; j >= 0; j--) {
            const dx = bullets[i].x - enemies[j].x;
            const dy = bullets[i].y - enemies[j].y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < bullets[i].radius + enemies[j].radius) {
                bullets.splice(i, 1);
                enemies.splice(j, 1);
                break;
            }
        }
    }
}

function drawCircle(entity) {
    ctx.beginPath();
    ctx.arc(entity.x, entity.y, entity.radius, 0, Math.PI * 2);
    ctx.fillStyle = entity.color;
    ctx.fill();
}

function drawBackground() {
    ctx.fillStyle = '#16213e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function gameLoop() {
    drawBackground();
    updatePlayer();
    updateBullets();
    updateEnemies();
    checkCollisions();
    
    drawCircle(player);
    bullets.forEach(drawCircle);
    enemies.forEach(drawCircle);
    
    requestAnimationFrame(gameLoop);
}

window.addEventListener('keydown', (e) => {
    keys[e.key] = true;
    e.preventDefault();
});
window.addEventListener('keyup', (e) => {
    keys[e.key] = false;
});
canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    shoot(e.clientX - rect.left, e.clientY - rect.top);
});

setInterval(spawnEnemy, 2000);
gameLoop();)JS",
        true,
        {}
    };
    shooterTpl->AddFileTemplate(shooterJs);
    
    RegisterTemplate(std::move(shooterTpl));
    
    // Default RPG Template
    TemplateMetadata rpgMeta = {
        "rpg-basic",
        "RPG Adventure Starter",
        "A basic RPG with player movement and simple NPC interaction",
        GameEngineType::Canvas2D,
        GameGenre::RPG,
        1,
        {"rpg", "adventure", "character", "npc"},
        true,
        88
    };
    auto rpgTpl = std::make_unique<SparkCraftTemplate>(rpgMeta);
    
    FileTemplate rpgHtml = {
        "{{GAME_NAME}}/index.html",
        R"HTML(<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{GAME_NAME}}</title>
    <style>
        body { margin: 0; padding: 0; background: #0f3460; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        canvas { border: 2px solid #16213e; }
        #dialog { position: absolute; bottom: 100px; background: rgba(0,0,0,0.9); color: white; padding: 20px; border-radius: 8px; display: none; max-width: 600px; }
    </style>
</head>
<body>
    <canvas id="gameCanvas" width="800" height="600"></canvas>
    <div id="dialog"></div>
    <script src="game.js"></script>
</body>
</html>)HTML",
        true,
        {}
    };
    rpgTpl->AddFileTemplate(rpgHtml);
    
    FileTemplate rpgJs = {
        "{{GAME_NAME}}/game.js",
        R"JS(// {{GAME_NAME}} - {{GAME_DESCRIPTION}}
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const dialogDiv = document.getElementById('dialog');

const player = {
    x: 400,
    y: 300,
    width: 24,
    height: 32,
    speed: 3,
    color: '#e94560'
};

const npcs = [
    { 
        x: 300, y: 200, 
        width: 24, height: 32, 
        color: '#533483',
        dialog: "Welcome, traveler! This is a peaceful village." 
    },
    { 
        x: 500, y: 400, 
        width: 24, height: 32, 
        color: '#00d9ff',
        dialog: "Beware of the dark forest to the east..." 
    }
];

const keys = {};
let currentDialog = null;

function updatePlayer() {
    if (currentDialog) return;
    
    if (keys['w'] || keys['ArrowUp']) player.y -= player.speed;
    if (keys['s'] || keys['ArrowDown']) player.y += player.speed;
    if (keys['a'] || keys['ArrowLeft']) player.x -= player.speed;
    if (keys['d'] || keys['ArrowRight']) player.x += player.speed;
    
    player.x = Math.max(0, Math.min(canvas.width - player.width, player.x));
    player.y = Math.max(0, Math.min(canvas.height - player.height, player.y));
}

function checkNPCInteraction() {
    for (let npc of npcs) {
        const dx = player.x - npc.x;
        const dy = player.y - npc.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 50 && keys['e'] && !currentDialog) {
            currentDialog = npc.dialog;
            dialogDiv.textContent = npc.dialog + " (Press Space to close)";
            dialogDiv.style.display = 'block';
        }
    }
}

function closeDialog() {
    if (currentDialog && keys[' ']) {
        currentDialog = null;
        dialogDiv.style.display = 'none';
    }
}

function drawCharacter(entity) {
    ctx.fillStyle = entity.color;
    ctx.fillRect(entity.x, entity.y, entity.width, entity.height);
    ctx.fillStyle = '#f9c74f';
    ctx.fillRect(entity.x + 4, entity.y - 16, entity.width - 8, 16);
}

function drawWorld() {
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#2d4a22';
    ctx.fillRect(100, 100, 600, 400);
    
    ctx.fillStyle = '#4a2222';
    ctx.fillRect(350, 250, 100, 100);
}

function gameLoop() {
    drawWorld();
    updatePlayer();
    checkNPCInteraction();
    closeDialog();
    
    npcs.forEach(drawCharacter);
    drawCharacter(player);
    
    requestAnimationFrame(gameLoop);
}

window.addEventListener('keydown', (e) => {
    keys[e.key] = true;
    e.preventDefault();
});
window.addEventListener('keyup', (e) => {
    keys[e.key] = false;
});

gameLoop();)JS",
        true,
        {}
    };
    rpgTpl->AddFileTemplate(rpgJs);
    
    RegisterTemplate(std::move(rpgTpl));
}

std::string SparkCraftSystem::AnalyzePrompt(const std::string& prompt) {
    return "Analyzed prompt: " + prompt.substr(0, std::min(50, (int)prompt.length()));
}

SparkCraftTemplate* SparkCraftSystem::SelectOptimalTemplate(const std::string& analysis, GameGenre genre) {
    auto candidates = FindTemplatesByGenre(genre);
    if (candidates.empty()) {
        // Fallback to any template
        if (!templates.empty()) {
            return templates.begin()->second.get();
        }
        return nullptr;
    }
    
    // Select template with highest success rate
    SparkCraftTemplate* best = candidates[0];
    for (auto tpl : candidates) {
        if (tpl->GetMetadata().successRate > best->GetMetadata().successRate) {
            best = tpl;
        }
    }
    return best;
}

} // namespace sparkai
} // namespace SparkLabs
