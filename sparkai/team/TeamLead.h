#ifndef SPARKLABS_TEAM_TEAMLEAD_H
#define SPARKLABS_TEAM_TEAMLEAD_H

#include "TeamAgent.h"

namespace SparkLabs {
namespace Team {

class TeamLead : public TeamAgent {
public:
    TeamLead(AgentRole role, const String& name);
    virtual ~TeamLead() = default;

    virtual String GenerateFeedback(const String& context) override;
    virtual bool ValidateTask(const Task& task) override;

    void DelegateTask(const Task& task, TeamAgent* specialist);
    void ConductReview(const Task& task);
    void ReportProgress();

    void AddSpecialist(TeamAgent* specialist);
    Vector<TeamAgent*> GetSpecialists() const { return m_Specialists; }

protected:
    Vector<TeamAgent*> m_Specialists;
    Vector<Task> m_PendingReviews;
};

} // namespace Team
} // namespace SparkLabs

#endif
