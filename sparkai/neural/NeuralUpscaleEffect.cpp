#include "NeuralUpscaleEffect.h"
#include "../Texture.h"

namespace SparkLabs {

NeuralUpscaleEffect::NeuralUpscaleEffect()
    : m_ScaleFactor(2.0f)
{
}

NeuralUpscaleEffect::~NeuralUpscaleEffect() {
}

void NeuralUpscaleEffect::Process(Texture* input, Texture* output) {
    if (!m_UpscaleModel || !input || !output) {
        return;
    }
}

void NeuralUpscaleEffect::SetScaleFactor(float32 factor) {
    m_ScaleFactor = factor;
}

}
