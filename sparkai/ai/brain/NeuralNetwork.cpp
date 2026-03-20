#include "NeuralNetwork.h"

namespace SparkLabs {

NeuralNetwork::NeuralNetwork()
    : m_UseGPU(false)
    , m_IsValid(false) {
}

NeuralNetwork::~NeuralNetwork() {
}

void NeuralNetwork::SetInferenceMode(bool useGPU) {
    m_UseGPU = useGPU;
}

}