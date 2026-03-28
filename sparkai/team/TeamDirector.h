#ifndef SPARKLABS_TEAM_TEAMDIRECTOR_H
#define SPARKLABS_TEAM_TEAMDIRECTOR_H

#include "TeamAgent.h"

namespace SparkLabs {
namespace Team {

class TeamDirector : public TeamAgent {
public:
    TeamDirector(AgentRole role, const String& name);
    virtual ~TeamDirector() = default;

    virtual String GenerateFeedback(const String& context) override;
    virtual bool ValidateTask(const Task& task) override;

    void SetVision(const String& vision);
    const String& GetVision() const { return m_Vision; }

    bool ApproveDesign(const String& designDoc);
    void EscalateIssue(const String& issue);

protected:
    String m_Vision;
    Vector<String> m_DesignReviews;
    Vector<String> m_EscalatedIssues;
};

} // namespace Team
} // namespace SparkLabs

#endif
