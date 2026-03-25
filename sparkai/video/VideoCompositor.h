#ifndef SPARKLABS_SPARKAI_VIDEO_VIDEOCOMPOSITOR_H
#define SPARKLABS_SPARKAI_VIDEO_VIDEOCOMPOSITOR_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "../../core/Map.h"
#include "../../core/Variant.h"
#include "../storyboard/Storyboard.h"
#include "../asset/AssetGenerator.h"
#include "../audio/VoiceSynthesis.h"

namespace SparkLabs {

enum class VideoResolution {
    SD_480p,
    HD_720p,
    FullHD_1080p,
    QHD_1440p,
    UHD_4K,
    UHD_8K
};

enum class VideoFormat {
    MP4,
    MOV,
    AVI,
    MKV,
    WEBM
};

enum class VideoCodec {
    H264,
    H265,
    VP9,
    AV1
};

struct VideoClip {
    StringHash id;
    String name;
    String filePath;
    float32 startTime;
    float32 duration;
    float32 playbackSpeed;
    float32 volume;
    int32 layer;
    Map<StringHash, Variant> effects;
    
    VideoClip()
        : id(StringHash())
        , startTime(0.0f)
        , duration(0.0f)
        , playbackSpeed(1.0f)
        , volume(1.0f)
        , layer(0)
    {}
};

struct AudioTrack {
    StringHash id;
    String name;
    SynthesizedAudio audio;
    float32 startTime;
    float32 volume;
    bool loop;
    int32 priority;
    
    AudioTrack()
        : id(StringHash())
        , startTime(0.0f)
        , volume(1.0f)
        , loop(false)
        , priority(0)
    {}
};

struct VideoEffect {
    StringHash id;
    String name;
    String type;
    Map<StringHash, Variant> parameters;
    float32 startTime;
    float32 duration;
    
    VideoEffect()
        : id(StringHash())
        , startTime(0.0f)
        , duration(0.0f)
    {}
};

struct RenderSettings {
    VideoResolution resolution;
    VideoFormat format;
    VideoCodec codec;
    int32 frameRate;
    int32 bitrate;
    bool includeAudio;
    String outputDirectory;
    String outputFilename;
    
    RenderSettings()
        : resolution(VideoResolution::FullHD_1080p)
        , format(VideoFormat::MP4)
        , codec(VideoCodec::H264)
        , frameRate(30)
        , bitrate(8000000)
        , includeAudio(true)
        , outputDirectory(String("./output"))
        , outputFilename(String("rendered_video"))
    {}
};

struct RenderProgress {
    float32 percentage;
    String currentStage;
    String currentTask;
    int32 totalFrames;
    int32 processedFrames;
    bool isComplete;
    bool hasError;
    String errorMessage;
    
    RenderProgress()
        : percentage(0.0f)
        , totalFrames(0)
        , processedFrames(0)
        , isComplete(false)
        , hasError(false)
    {}
};

class VideoCompositor {
public:
    VideoCompositor();
    ~VideoCompositor();
    
    void SetStoryboard(Storyboard* storyboard) { m_Storyboard = storyboard; }
    Storyboard* GetStoryboard() const { return m_Storyboard; }
    
    void SetRenderSettings(const RenderSettings& settings) { m_RenderSettings = settings; }
    const RenderSettings& GetRenderSettings() const { return m_RenderSettings; }
    
    VideoClip* AddVideoClip(const String& name, const String& filePath);
    void RemoveVideoClip(const StringHash& clipId);
    VideoClip* GetVideoClip(const StringHash& clipId);
    Vector<VideoClip*> GetAllVideoClips();
    
    AudioTrack* AddAudioTrack(const String& name, const SynthesizedAudio& audio);
    void RemoveAudioTrack(const StringHash& trackId);
    AudioTrack* GetAudioTrack(const StringHash& trackId);
    Vector<AudioTrack*> GetAllAudioTracks();
    
    VideoEffect* AddVideoEffect(const String& name, const String& type);
    void RemoveVideoEffect(const StringHash& effectId);
    VideoEffect* GetVideoEffect(const StringHash& effectId);
    Vector<VideoEffect*> GetAllVideoEffects();
    
    void GenerateClipsFromStoryboard();
    void GenerateAudioFromStoryboard();
    
    void StartRender();
    void StopRender();
    bool IsRendering() const { return m_IsRendering; }
    
    RenderProgress GetRenderProgress() const { return m_RenderProgress; }
    
    String GetOutputFilePath() const;
    float32 GetTotalDuration() const;
    
    void SetMetadata(const StringHash& key, const Variant& value);
    Variant GetMetadata(const StringHash& key) const;
    
    bool SaveProject(const String& filePath);
    bool LoadProject(const String& filePath);
    
private:
    StringHash GenerateUniqueId();
    void RenderThread();
    void UpdateProgress(float32 percentage, const String& stage, const String& task);
    
    Storyboard* m_Storyboard;
    RenderSettings m_RenderSettings;
    RenderProgress m_RenderProgress;
    
    Vector< SmartPtr<VideoClip> > m_VideoClips;
    Vector< SmartPtr<AudioTrack> > m_AudioTracks;
    Vector< SmartPtr<VideoEffect> > m_VideoEffects;
    
    Map<StringHash, Variant> m_Metadata;
    uint64 m_IdCounter;
    bool m_IsRendering;
    bool m_ShouldStop;
};

}

#endif
