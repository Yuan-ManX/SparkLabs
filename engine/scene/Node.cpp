#include "Node.h"
#include "Transform.h"

namespace SparkLabs {

Node::Node()
    : m_LocalPosition(Vector3::Zero())
    , m_LocalRotation(Quaternion::Identity())
    , m_LocalScale(Vector3::One())
    , m_Dirty(true)
    , m_Active(true)
    , m_Visible(true)
    , m_WorldTransformDirty(true)
{
}

Node::~Node() {
    for (auto& child : m_Children) {
        child->SetParent(nullptr);
    }
    m_Children.Clear();
    if (m_Parent) {
        m_Parent->RemoveChild(this);
    }
}

void Node::SetName(const String& name) {
    m_Name = name;
}

const String& Node::GetName() const {
    return m_Name;
}

void Node::SetPosition(const Vector3& position) {
    if (m_Parent) {
        Matrix4x4 invParent = m_Parent->GetWorldTransformMatrix().Inverse();
        m_LocalPosition = invParent.TransformPoint(position);
    } else {
        m_LocalPosition = position;
    }
    SetDirty();
}

Vector3 Node::GetPosition() const {
    return GetWorldTransformMatrix().GetTranslation();
}

void Node::SetRotation(const Quaternion& rotation) {
    if (m_Parent) {
        Quaternion invParentRot = m_Parent->GetWorldTransformMatrix().ExtractRotation().Inverse();
        m_LocalRotation = invParentRot * rotation;
    } else {
        m_LocalRotation = rotation;
    }
    SetDirty();
}

Quaternion Node::GetRotation() const {
    return GetWorldTransformMatrix().ExtractRotation();
}

void Node::SetScale(const Vector3& scale) {
    if (m_Parent) {
        m_LocalScale = scale / m_Parent->GetScale();
    } else {
        m_LocalScale = scale;
    }
    SetDirty();
}

Vector3 Node::GetScale() const {
    return GetWorldTransformMatrix().ExtractScale();
}

void Node::SetLocalPosition(const Vector3& position) {
    m_LocalPosition = position;
    SetDirty();
}

Vector3 Node::GetLocalPosition() const {
    return m_LocalPosition;
}

void Node::SetLocalRotation(const Quaternion& rotation) {
    m_LocalRotation = rotation;
    SetDirty();
}

Quaternion Node::GetLocalRotation() const {
    return m_LocalRotation;
}

void Node::SetLocalScale(const Vector3& scale) {
    m_LocalScale = scale;
    SetDirty();
}

Vector3 Node::GetLocalScale() const {
    return m_LocalScale;
}

Matrix4x4 Node::GetLocalTransformMatrix() const {
    return Transform::ComposeTransform(m_LocalPosition, m_LocalRotation, m_LocalScale);
}

Matrix4x4 Node::GetWorldTransformMatrix() const {
    if (m_WorldTransformDirty) {
        UpdateWorldTransform();
    }
    return m_WorldTransform;
}

void Node::UpdateWorldTransform() const {
    if (m_Parent) {
        m_WorldTransform = m_Parent->GetWorldTransformMatrix() * GetLocalTransformMatrix();
    } else {
        m_WorldTransform = GetLocalTransformMatrix();
    }
    m_WorldTransformDirty = false;
}

void Node::LookAt(const Vector3& target) {
    LookAt(target, Vector3::Up());
}

void Node::LookAt(const Vector3& target, const Vector3& up) {
    Vector3 forward = (target - GetPosition()).Normalized();
    Vector3 right = Vector3::Cross(forward, up).Normalized();
    Vector3 newUp = Vector3::Cross(right, forward);
    Quaternion rotation = Quaternion::FromLookRotation(forward, newUp);
    SetRotation(rotation);
}

Vector3 Node::GetForward() const {
    return GetRotation() * Vector3::Forward();
}

Vector3 Node::GetRight() const {
    return GetRotation() * Vector3::Right();
}

Vector3 Node::GetUp() const {
    return GetRotation() * Vector3::Up();
}

Node* Node::GetParent() const {
    return m_Parent.Get();
}

void Node::SetParent(Node* parent) {
    if (m_Parent == parent) return;
    if (m_Parent) {
        m_Parent->RemoveChild(this);
    }
    m_Parent = parent;
    SetDirty();
}

void Node::AddChild(Node* child) {
    if (!child) return;
    child->SetParent(this);
    m_Children.PushBack(SmartPtr<Node>(child));
}

void Node::RemoveChild(Node* child) {
    for (size_t i = 0; i < m_Children.Size(); ++i) {
        if (m_Children[i].Get() == child) {
            m_Children.Erase(i);
            return;
        }
    }
}

void Node::RemoveFromParent() {
    if (m_Parent) {
        m_Parent->RemoveChild(this);
    }
    m_Parent = nullptr;
}

int Node::GetChildCount() const {
    return m_Children.Size();
}

Node* Node::GetChild(int index) {
    if (index >= 0 && index < m_Children.Size()) {
        return m_Children[index].Get();
    }
    return nullptr;
}

void Node::SetDirty(bool dirty) {
    m_Dirty = dirty;
    if (dirty && !m_WorldTransformDirty) {
        m_WorldTransformDirty = true;
        for (auto& child : m_Children) {
            child->SetDirty(true);
        }
        OnTransformChanged();
    }
}

bool Node::IsDirty() const {
    return m_Dirty;
}

void Node::SetActive(bool active) {
    m_Active = active;
}

bool Node::IsActive() const {
    if (!m_Active) return false;
    if (m_Parent) return m_Parent->IsActive();
    return true;
}

void Node::SetVisible(bool visible) {
    m_Visible = visible;
}

bool Node::IsVisible() const {
    if (!m_Visible) return false;
    if (m_Parent) return m_Parent->IsVisible();
    return true;
}

void Node::OnTransformChanged() {
}

}
