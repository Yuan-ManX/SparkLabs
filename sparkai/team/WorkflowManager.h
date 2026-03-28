#ifndef SPARKLABS_TEAM_WORKFLOWMANAGER_H
#define SPARKLABS_TEAM_WORKFLOWMANAGER_H

#include "../core/Types.h"
#include "../core/string/String.h"
#include "TeamAgent.h"

namespace SparkLabs {
namespace Team {

enum class WorkflowType {
    Brainstorm,
    SprintPlan,
    DesignReview,
    CodeReview,
    BalanceCheck,
    AssetAudit,
    ScopeCheck,
    PerformanceProfile,
    TechDebt,
    MilestoneReview,
    Estimate,
    Retrospective,
    BugReport,
    ReleaseChecklist,
    LaunchChecklist,
    Changelog,
    PatchNotes,
    Hotfix,
    TeamCombat,
    TeamNarrative,
    TeamUI,
    TeamRelease,
    TeamPolish,
    TeamAudio,
    TeamLevel
};

struct WorkflowStep {
    String id;
    String name;
    String description;
    AgentRole responsibleRole;
    bool completed;
};

struct WorkflowTemplate {
    String id;
    String name;
    WorkflowType type;
    Vector<WorkflowStep> steps;
    String description;
};

class WorkflowManager {
public:
    static WorkflowManager* GetInstance();

    void Initialize();
    void Shutdown();

    void StartWorkflow(WorkflowType type, const String& context);
    void AdvanceWorkflow();
    void CompleteWorkflow();

    WorkflowTemplate* GetCurrentWorkflow() { return m_CurrentWorkflow.Get(); }
    Vector<WorkflowTemplate> GetAvailableWorkflows() const { return m_AvailableWorkflows; }

    void RegisterWorkflow(const WorkflowTemplate& workflow);
    void CreateCustomWorkflow(const String& name, const Vector<WorkflowStep>& steps);

    String GetWorkflowStatus() const;
    Vector<String> GetWorkflowHistory() const { return m_WorkflowHistory; }

private:
    WorkflowManager();
    ~WorkflowManager();

    static WorkflowManager* s_Instance;

    void InitializeDefaultWorkflows();

    SmartPtr<WorkflowTemplate> m_CurrentWorkflow;
    Vector<WorkflowTemplate> m_AvailableWorkflows;
    Vector<String> m_WorkflowHistory;
    size_t m_CurrentStepIndex;
    bool m_Initialized;
};

} // namespace Team
} // namespace SparkLabs

#endif
