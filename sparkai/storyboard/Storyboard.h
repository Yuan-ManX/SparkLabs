#ifndef SPARKLABS_SPARKAI_STORYBOARD_STORYBOARD_H
#define SPARKLABS_SPARKAI_STORYBOARD_STORYBOARD_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "../../core/Map.h"
#include "../../core/Variant.h"
#include "../../core/math/Vector2.h"
#include "../narrative/StoryParser.h"

namespace SparkLabs {

enum class ShotType {
    Wide,
    Medium,
    CloseUp,
    ExtremeCloseUp,
    OverTheShoulder,
    LowAngle,
    HighAngle,
    BirdEye,
    Dutch,
    Insert
};

enum class CameraMovement {
    Static,
    Pan,
    Tilt,
    Dolly,
    Track,
    Crane,
    Zoom,
    Handheld,
    Steadicam
};

enum class TransitionType {
    Cut,
    Dissolve,
    Wipe,
    FadeIn,
    FadeOut,
    CrossFade,
    Iris,
    Morph
};

struct StoryboardFrame {
    StringHash id;
    int32 order;
    String title;
    String description;
    String action;
    String dialogue;
    StringHash sceneId;
    Vector<StringHash> characterIds;
    
    ShotType shotType;
    CameraMovement cameraMovement;
    Vector2 cameraAngle;
    float32 cameraZoom;
    float32 duration;
    
    TransitionType transitionIn;
    TransitionType transitionOut;
    float32 transitionDuration;
    
    StringHash assetId;
    StringHash audioId;
    Vector<StringHash> effectIds;
    
    Map<StringHash, Variant> metadata;
    
    StoryboardFrame()
        : id(StringHash())
        , order(0)
        , shotType(ShotType::Medium)
        , cameraMovement(CameraMovement::Static)
        , cameraAngle(Vector2(0.0f, 0.0f))
        , cameraZoom(1.0f)
        , duration(3.0f)
        , transitionIn(TransitionType::Cut)
        , transitionOut(TransitionType::Cut)
        , transitionDuration(0.5f)
        , assetId(StringHash())
        , audioId(StringHash())
    {}
};

struct StoryboardSequence {
    StringHash id;
    String name;
    String description;
    Vector<StoryboardFrame> frames;
    float32 totalDuration;
    StringHash storyBeatId;
    Map<StringHash, Variant> metadata;
    
    StoryboardSequence()
        : id(StringHash())
        , totalDuration(0.0f)
        , storyBeatId(StringHash())
    {}
};

class Storyboard {
public:
    Storyboard();
    ~Storyboard();
    
    void SetName(const String& name) { m_Name = name; }
    const String& GetName() const { return m_Name; }
    
    StoryboardSequence* CreateSequence(const String& name);
    void AddSequence(StoryboardSequence* sequence);
    void RemoveSequence(const StringHash& sequenceId);
    StoryboardSequence* GetSequence(const StringHash& sequenceId);
    Vector<StoryboardSequence*> GetAllSequences();
    
    StoryboardFrame* CreateFrame(StoryboardSequence* sequence, const String& title);
    void AddFrame(StoryboardSequence* sequence, StoryboardFrame* frame);
    void RemoveFrame(StoryboardSequence* sequence, const StringHash& frameId);
    void ReorderFrames(StoryboardSequence* sequence, const Vector<StringHash>& newOrder);
    
    void GenerateFromStoryAnalysis(const StoryAnalysisResult& analysis);
    void AutoGenerateTransitions();
    void AutoCalculateDurations();
    
    float32 GetTotalDuration() const;
    int32 GetTotalFrameCount() const;
    
    void SetMetadata(const StringHash& key, const Variant& value);
    Variant GetMetadata(const StringHash& key) const;
    
    bool SaveToFile(const String& filePath);
    bool LoadFromFile(const String& filePath);
    
private:
    StringHash GenerateUniqueId();
    void UpdateSequenceDuration(StoryboardSequence* sequence);
    
    String m_Name;
    Vector< SmartPtr<StoryboardSequence> > m_Sequences;
    Map<StringHash, Variant> m_Metadata;
    uint64 m_IdCounter;
};

}

#endif
