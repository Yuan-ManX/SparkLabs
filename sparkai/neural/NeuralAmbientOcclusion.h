#ifndef SPARKAI_RENDER_NEURAL_AMBIENTOCCLUSION_H
#define SPARKAI_RENDER_NEURAL_AMBIENTOCCLUSION_H

#include "../../core/Types.h"
#include "../../core/memory/SmartPtr.h"
#include "../../ai/brain/NeuralNetwork.h"

namespace SparkLabs {

class Texture;
class RenderContext;

class NeuralAmbientOcclusion {
public:
    NeuralAmbientOcclusion();
    ~NeuralAmbientOcclusion();

    void Render(const RenderContext& context, Texture* depth, Texture* normal, Texture* output);

    void SetModel(SmartPtr<NeuralNetwork> model) { m_AOModel = model; }
    SmartPtr<NeuralNetwork> GetModel() const { return m_AOModel; }

    void SetStrength(float32 strength) { m_Strength = strength; }
    float32 GetStrength() const { return m_Strength; }

    void SetRadius(float32 radius) { m_Radius = radius; }
    float32 GetRadius() const { return m_Radius; }

    bool IsValid() const { return m_AOModel != nullptr; }

private:
    SmartPtr<NeuralNetwork> m_AOModel;
    float32 m_Strength;
    float32 m_Radius;
};

}

#endif
