#include "TeamLead.h"

namespace SparkLabs {
namespace Team {

TeamLead::TeamLead(AgentRole role, const String& name)
    : TeamAgent(role, AgentTier::Lead, name) {
}

String TeamLead::GenerateFeedback(const String& context) {
    return String("Lead feedback on: ") + context;
}

bool TeamLead::ValidateTask(const Task& task) {
    return !task.title.IsEmpty() && task.progress >= 0.0f && task.progress <= 1.0f;
}

void TeamLead::DelegateTask(const Task& task, TeamAgent* specialist) {
    if (specialist && specialist->GetTier() == AgentTier::Specialist) {
        specialist->AssignTask(task);
    }
}

void TeamLead::ConductReview(const Task& task) {
    m_PendingReviews.PushBack(task);
}

void TeamLead::ReportProgress() {
}

void TeamLead::AddSpecialist(TeamAgent* specialist) {
    if (specialist) {
        m_Specialists.PushBack(specialist);
    }
}

} // namespace Team
} // namespace SparkLabs
