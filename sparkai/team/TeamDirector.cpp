#include "TeamDirector.h"

namespace SparkLabs {
namespace Team {

TeamDirector::TeamDirector(AgentRole role, const String& name)
    : TeamAgent(role, AgentTier::Director, name) {
}

String TeamDirector::GenerateFeedback(const String& context) {
    return String("Director feedback on: ") + context;
}

bool TeamDirector::ValidateTask(const Task& task) {
    return !task.title.IsEmpty() && !task.description.IsEmpty();
}

void TeamDirector::SetVision(const String& vision) {
    m_Vision = vision;
}

bool TeamDirector::ApproveDesign(const String& designDoc) {
    m_DesignReviews.PushBack(designDoc);
    return true;
}

void TeamDirector::EscalateIssue(const String& issue) {
    m_EscalatedIssues.PushBack(issue);
}

} // namespace Team
} // namespace SparkLabs
