#ifndef SPARKLABS_SPARKAI_AUDIO_VOICESYNTHESIS_H
#define SPARKLABS_SPARKAI_AUDIO_VOICESYNTHESIS_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "../../core/Map.h"
#include "../../core/Variant.h"

namespace SparkLabs {

enum class VoiceGender {
    Male,
    Female,
    Neutral
};

enum class VoiceEmotion {
    Neutral,
    Happy,
    Sad,
    Angry,
    Fearful,
    Surprised,
    Excited,
    Calm
};

struct VoiceProfile {
    StringHash id;
    String name;
    VoiceGender gender;
    float32 pitch;
    float32 speed;
    float32 volume;
    String language;
    String accent;
    Vector<String> tags;
    Map<StringHash, Variant> metadata;

    VoiceProfile()
        : id(StringHash())
        , gender(VoiceGender::Neutral)
        , pitch(1.0f)
        , speed(1.0f)
        , volume(1.0f)
        , language(String("en"))
    {}
};

struct SpeechRequest {
    String text;
    StringHash voiceId;
    VoiceEmotion emotion;
    float32 pitch;
    float32 speed;
    float32 volume;
    int32 sampleRate;
    Map<StringHash, Variant> parameters;

    SpeechRequest()
        : emotion(VoiceEmotion::Neutral)
        , pitch(1.0f)
        , speed(1.0f)
        , volume(1.0f)
        , sampleRate(44100)
    {}
};

struct SynthesizedAudio {
    StringHash id;
    String filePath;
    Vector<uint8> data;
    int32 sampleRate;
    int32 channels;
    int32 bitsPerSample;
    size_t totalSamples;
    float32 duration;
    Map<StringHash, Variant> metadata;
    SpeechRequest request;

    SynthesizedAudio()
        : id(StringHash())
        , sampleRate(44100)
        , channels(1)
        , bitsPerSample(16)
        , totalSamples(0)
        , duration(0.0f)
    {}
};

struct DialogueLine {
    StringHash id;
    StringHash speakerId;
    String speakerName;
    String text;
    VoiceEmotion emotion;
    float32 startTime;
    float32 duration;
    Map<StringHash, Variant> metadata;

    DialogueLine()
        : id(StringHash())
        , speakerId(StringHash())
        , emotion(VoiceEmotion::Neutral)
        , startTime(0.0f)
        , duration(0.0f)
    {}
};

struct DialogueSequence {
    StringHash id;
    String name;
    Vector<DialogueLine> lines;
    float32 totalDuration;
    Map<StringHash, Variant> metadata;

    DialogueSequence() : id(StringHash()), totalDuration(0.0f) {}
};

class VoiceSynthesis {
public:
    VoiceSynthesis();
    ~VoiceSynthesis();

    SynthesizedAudio SynthesizeSpeech(const SpeechRequest& request);
    SynthesizedAudio SynthesizeDialogueLine(const DialogueLine& line, const VoiceProfile& voice);
    Vector<SynthesizedAudio> SynthesizeSequence(const DialogueSequence& sequence, const Map<StringHash, VoiceProfile>& voices);

    void RegisterVoice(const VoiceProfile& voice);
    void UnregisterVoice(const StringHash& voiceId);
    VoiceProfile* GetVoice(const StringHash& voiceId);
    Vector<VoiceProfile> GetAllVoices() const;

    void SetDefaultVoice(const StringHash& voiceId) { m_DefaultVoiceId = voiceId; }
    StringHash GetDefaultVoiceId() const { return m_DefaultVoiceId; }

    void SetOutputDirectory(const String& path) { m_OutputDirectory = path; }
    const String& GetOutputDirectory() const { return m_OutputDirectory; }

    bool SaveAudio(const SynthesizedAudio& audio, const String& filePath);
    SynthesizedAudio LoadAudio(const String& filePath);

    void SetSampleRate(int32 rate) { m_DefaultSampleRate = rate; }
    int32 GetSampleRate() const { return m_DefaultSampleRate; }

private:
    StringHash GenerateUniqueId();
    SynthesizedAudio CreatePlaceholderAudio(const String& text);
    float32 EstimateDuration(const String& text, float32 speed);

    Map<StringHash, VoiceProfile> m_Voices;
    StringHash m_DefaultVoiceId;
    String m_OutputDirectory;
    int32 m_DefaultSampleRate;
    uint64 m_IdCounter;
};

}

#endif
