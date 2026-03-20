#ifndef SPARKAI_RENDER_NEURAL_ANTIALIAS_H
#define SPARKAI_RENDER_NEURAL_ANTIALIAS_H

#include "../../core/Types.h"
#include "../../core/memory/SmartPtr.h"
#include "../../ai/brain/NeuralNetwork.h"

namespace SparkLabs {

class Texture;
class Camera;

class NeuralAntiAlias {
public:
    NeuralAntiAlias();

    enum class AAMode {
        FXAA,
        TAA,
        NeuralAA
    };

    void Process(Texture* input, Texture* output, const Camera* camera);

    void SetModel(SmartPtr<NeuralNetwork> model) { m_AAModel = model; }
    SmartPtr<NeuralNetwork> GetModel() const { return m_AAModel; }

    void SetMode(AAMode mode) { m_Mode = mode; }
    AAMode GetMode() const { return m_Mode; }

    bool IsValid() const { return m_AAModel != nullptr; }

private:
    SmartPtr<NeuralNetwork> m_AAModel;
    AAMode m_Mode;
};

}

#endif
