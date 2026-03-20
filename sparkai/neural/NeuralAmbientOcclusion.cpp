#include "NeuralAmbientOcclusion.h"
#include "../Texture.h"
#include "../RenderContext.h"

namespace SparkLabs {

NeuralAmbientOcclusion::NeuralAmbientOcclusion()
    : m_Strength(1.0f)
    , m_Radius(1.0f)
{
}

NeuralAmbientOcclusion::~NeuralAmbientOcclusion() {
}

void NeuralAmbientOcclusion::Render(const RenderContext& context, Texture* depth, Texture* normal, Texture* output) {
    if (!m_AOModel || !depth || !normal || !output) {
        return;
    }
}

}
