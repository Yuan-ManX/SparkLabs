#include "TeamOrchestrator.h"

namespace SparkLabs {
namespace Team {

TeamOrchestrator* TeamOrchestrator::s_Instance = nullptr;

TeamOrchestrator::TeamOrchestrator()
    : m_Initialized(false) {
}

TeamOrchestrator::~TeamOrchestrator() {
    if (m_Initialized) {
        Shutdown();
    }
}

TeamOrchestrator* TeamOrchestrator::GetInstance() {
    if (!s_Instance) {
        s_Instance = new TeamOrchestrator();
    }
    return s_Instance;
}

void TeamOrchestrator::Initialize() {
    if (m_Initialized) {
        return;
    }

    m_CreativeDirector = SmartPtr<TeamDirector>(
        new TeamDirector(AgentRole::CreativeDirector, "Creative Director"));
    m_TechnicalDirector = SmartPtr<TeamDirector>(
        new TeamDirector(AgentRole::TechnicalDirector, "Technical Director"));
    m_Producer = SmartPtr<TeamDirector>(
        new TeamDirector(AgentRole::Producer, "Producer"));

    m_AllAgents.PushBack(m_CreativeDirector.Get());
    m_AllAgents.PushBack(m_TechnicalDirector.Get());
    m_AllAgents.PushBack(m_Producer.Get());

    m_AgentMap[m_CreativeDirector->GetName()] = m_CreativeDirector.Get();
    m_AgentMap[m_TechnicalDirector->GetName()] = m_TechnicalDirector.Get();
    m_AgentMap[m_Producer->GetName()] = m_Producer.Get();

    m_CreativeDirector->Initialize();
    m_TechnicalDirector->Initialize();
    m_Producer->Initialize();

    m_Initialized = true;
}

void TeamOrchestrator::Shutdown() {
    if (!m_Initialized) {
        return;
    }

    for (auto agent : m_AllAgents) {
        agent->Shutdown();
    }

    m_CreativeDirector = nullptr;
    m_TechnicalDirector = nullptr;
    m_Producer = nullptr;

    m_AllAgents.Clear();
    m_ActiveTasks.Clear();
    m_AgentMap.Clear();

    m_Initialized = false;
}

void TeamOrchestrator::Update(float32 deltaTime) {
    if (!m_Initialized) {
        return;
    }

    for (auto agent : m_AllAgents) {
        agent->Update(deltaTime);
    }
}

void TeamOrchestrator::AddAgent(TeamAgent* agent) {
    if (!agent) {
        return;
    }

    m_AllAgents.PushBack(agent);
    m_AgentMap[agent->GetName()] = agent;
    agent->Initialize();
}

void TeamOrchestrator::RemoveAgent(const String& name) {
    TeamAgent** agentPtr = m_AgentMap.Find(name);
    if (agentPtr != nullptr) {
        TeamAgent* agent = *agentPtr;
        agent->Shutdown();

        for (size_t i = 0; i < m_AllAgents.Size(); ++i) {
            if (m_AllAgents[i] == agent) {
                m_AllAgents.Erase(i);
                break;
            }
        }
        m_AgentMap.Remove(name);
    }
}

TeamAgent* TeamOrchestrator::GetAgent(const String& name) {
    TeamAgent** agentPtr = m_AgentMap.Find(name);
    if (agentPtr != nullptr) {
        return *agentPtr;
    }
    return nullptr;
}

void TeamOrchestrator::CreateTask(const String& title, const String& description, AgentRole assignedTo) {
    Task task;
    task.id = "task_" + String::FromInt(m_ActiveTasks.Size());
    task.title = title;
    task.description = description;
    task.assignedTo = assignedTo;
    task.status = TaskStatus::Pending;
    task.progress = 0.0f;
    task.createdBy = "System";

    m_ActiveTasks.PushBack(task);
}

void TeamOrchestrator::AssignTask(const String& taskId, AgentRole role) {
    for (auto& task : m_ActiveTasks) {
        if (task.id == taskId) {
            task.assignedTo = role;
            task.status = TaskStatus::InProgress;

            for (auto agent : m_AllAgents) {
                if (agent->GetRole() == role) {
                    agent->AssignTask(task);
                    break;
                }
            }
            break;
        }
    }
}

void TeamOrchestrator::ConductDesignReview(const String& design) {
    if (m_CreativeDirector) {
        m_CreativeDirector->ApproveDesign(design);
    }
}

void TeamOrchestrator::ConductCodeReview(const String& code) {
    if (m_TechnicalDirector) {
        m_TechnicalDirector->GenerateFeedback(code);
    }
}

} // namespace Team
} // namespace SparkLabs
