#ifndef SPARKLABS_TEAM_TEAMORCHESTRATOR_H
#define SPARKLABS_TEAM_TEAMORCHESTRATOR_H

#include "TeamAgent.h"
#include "TeamDirector.h"
#include "TeamLead.h"
#include "TeamSpecialist.h"
#include "../core/memory/SmartPtr.h"

namespace SparkLabs {
namespace Team {

class TeamOrchestrator {
public:
    static TeamOrchestrator* GetInstance();

    void Initialize();
    void Shutdown();
    void Update(float32 deltaTime);

    void AddAgent(TeamAgent* agent);
    void RemoveAgent(const String& name);
    TeamAgent* GetAgent(const String& name);

    void CreateTask(const String& title, const String& description, AgentRole assignedTo);
    void AssignTask(const String& taskId, AgentRole role);

    void ConductDesignReview(const String& design);
    void ConductCodeReview(const String& code);

    TeamDirector* GetCreativeDirector() { return m_CreativeDirector.Get(); }
    TeamDirector* GetTechnicalDirector() { return m_TechnicalDirector.Get(); }
    TeamDirector* GetProducer() { return m_Producer.Get(); }

    Vector<TeamAgent*> GetAllAgents() const { return m_AllAgents; }
    Vector<Task> GetActiveTasks() const { return m_ActiveTasks; }

private:
    TeamOrchestrator();
    ~TeamOrchestrator();

    static TeamOrchestrator* s_Instance;

    SmartPtr<TeamDirector> m_CreativeDirector;
    SmartPtr<TeamDirector> m_TechnicalDirector;
    SmartPtr<TeamDirector> m_Producer;

    Vector<TeamAgent*> m_AllAgents;
    Vector<Task> m_ActiveTasks;
    Map<String, TeamAgent*> m_AgentMap;

    bool m_Initialized;
};

} // namespace Team
} // namespace SparkLabs

#endif
