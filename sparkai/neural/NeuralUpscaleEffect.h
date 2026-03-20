#ifndef SPARKAI_RENDER_NEURAL_UPSCaleeFFECT_H
#define SPARKAI_RENDER_NEURAL_UPSCaleeFFECT_H

#include "../../core/Types.h"
#include "../../core/memory/SmartPtr.h"
#include "../../ai/brain/NeuralNetwork.h"

namespace SparkLabs {

class Texture;

class NeuralUpscaleEffect {
public:
    NeuralUpscaleEffect();
    ~NeuralUpscaleEffect();

    void Process(Texture* input, Texture* output);
    void SetScaleFactor(float32 factor);
    float32 GetScaleFactor() const { return m_ScaleFactor; }

    void SetModel(SmartPtr<NeuralNetwork> model) { m_UpscaleModel = model; }
    SmartPtr<NeuralNetwork> GetModel() const { return m_UpscaleModel; }

    bool IsValid() const { return m_UpscaleModel != nullptr; }

private:
    SmartPtr<NeuralNetwork> m_UpscaleModel;
    float32 m_ScaleFactor;
};

}

#endif
