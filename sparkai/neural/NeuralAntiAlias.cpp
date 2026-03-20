#include "NeuralAntiAlias.h"
#include "../Texture.h"
#include "../RenderDevice.h"

namespace SparkLabs {

NeuralAntiAlias::NeuralAntiAlias()
    : m_Mode(AAMode::NeuralAA)
{
}

void NeuralAntiAlias::Process(Texture* input, Texture* output, const Camera* camera) {
    if (!m_AAModel || !input || !output) {
        return;
    }
}

}
