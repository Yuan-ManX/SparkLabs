#include "WorkflowManager.h"

namespace SparkLabs {
namespace Team {

WorkflowManager* WorkflowManager::s_Instance = nullptr;

WorkflowManager::WorkflowManager()
    : m_CurrentWorkflow(nullptr)
    , m_CurrentStepIndex(0)
    , m_Initialized(false) {
}

WorkflowManager::~WorkflowManager() {
    if (m_Initialized) {
        Shutdown();
    }
}

WorkflowManager* WorkflowManager::GetInstance() {
    if (!s_Instance) {
        s_Instance = new WorkflowManager();
    }
    return s_Instance;
}

void WorkflowManager::Initialize() {
    if (m_Initialized) {
        return;
    }

    InitializeDefaultWorkflows();
    m_Initialized = true;
}

void WorkflowManager::Shutdown() {
    if (!m_Initialized) {
        return;
    }

    m_CurrentWorkflow = nullptr;
    m_AvailableWorkflows.Clear();
    m_WorkflowHistory.Clear();
    m_CurrentStepIndex = 0;
    m_Initialized = false;
}

void WorkflowManager::InitializeDefaultWorkflows() {
    WorkflowTemplate brainstorm;
    brainstorm.id = "brainstorm";
    brainstorm.name = "Brainstorm Session";
    brainstorm.type = WorkflowType::Brainstorm;
    brainstorm.description = "Creative ideation and concept exploration";

    WorkflowStep step1;
    step1.id = "step1";
    step1.name = "Define Problem";
    step1.description = "Clearly define the problem or opportunity";
    step1.responsibleRole = AgentRole::CreativeDirector;
    step1.completed = false;
    brainstorm.steps.PushBack(step1);

    WorkflowStep step2;
    step2.id = "step2";
    step2.name = "Generate Ideas";
    step2.description = "Brainstorm creative solutions and concepts";
    step2.responsibleRole = AgentRole::GameDesigner;
    step2.completed = false;
    brainstorm.steps.PushBack(step2);

    m_AvailableWorkflows.PushBack(brainstorm);

    WorkflowTemplate designReview;
    designReview.id = "design_review";
    designReview.name = "Design Review";
    designReview.type = WorkflowType::DesignReview;
    designReview.description = "Review and validate design documents";
    m_AvailableWorkflows.PushBack(designReview);

    WorkflowTemplate codeReview;
    codeReview.id = "code_review";
    codeReview.name = "Code Review";
    codeReview.type = WorkflowType::CodeReview;
    codeReview.description = "Review code for quality and standards compliance";
    m_AvailableWorkflows.PushBack(codeReview);

    WorkflowTemplate sprintPlan;
    sprintPlan.id = "sprint_plan";
    sprintPlan.name = "Sprint Planning";
    sprintPlan.type = WorkflowType::SprintPlan;
    sprintPlan.description = "Plan and prioritize upcoming work";
    m_AvailableWorkflows.PushBack(sprintPlan);
}

void WorkflowManager::StartWorkflow(WorkflowType type, const String& context) {
    for (auto& workflow : m_AvailableWorkflows) {
        if (workflow.type == type) {
            m_CurrentWorkflow = SmartPtr<WorkflowTemplate>(new WorkflowTemplate(workflow));
            m_CurrentStepIndex = 0;

            for (auto& step : m_CurrentWorkflow->steps) {
                step.completed = false;
            }

            m_WorkflowHistory.PushBack(String("Started: ") + workflow.name + " - " + context);
            break;
        }
    }
}

void WorkflowManager::AdvanceWorkflow() {
    if (!m_CurrentWorkflow) {
        return;
    }

    if (m_CurrentStepIndex < m_CurrentWorkflow->steps.Size()) {
        m_CurrentWorkflow->steps[m_CurrentStepIndex].completed = true;
        m_CurrentStepIndex++;
    }
}

void WorkflowManager::CompleteWorkflow() {
    if (!m_CurrentWorkflow) {
        return;
    }

    for (auto& step : m_CurrentWorkflow->steps) {
        step.completed = true;
    }

    m_WorkflowHistory.PushBack(String("Completed: ") + m_CurrentWorkflow->name);
    m_CurrentWorkflow = nullptr;
    m_CurrentStepIndex = 0;
}

void WorkflowManager::RegisterWorkflow(const WorkflowTemplate& workflow) {
    m_AvailableWorkflows.PushBack(workflow);
}

void WorkflowManager::CreateCustomWorkflow(const String& name, const Array<WorkflowStep>& steps) {
    WorkflowTemplate custom;
    custom.id = "custom_" + String::FromInt(m_AvailableWorkflows.Size());
    custom.name = name;
    custom.type = WorkflowType::Brainstorm;
    custom.steps = steps;
    m_AvailableWorkflows.PushBack(custom);
}

String WorkflowManager::GetWorkflowStatus() const {
    if (!m_CurrentWorkflow) {
        return "No active workflow";
    }

    return String("Current: ") + m_CurrentWorkflow->name +
        " (Step " + String::FromInt(m_CurrentStepIndex + 1) +
        " of " + String::FromInt(m_CurrentWorkflow->steps.Size()) + ")";
}

} // namespace Team
} // namespace SparkLabs
