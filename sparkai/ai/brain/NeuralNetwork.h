#ifndef SPARKAI_AI_BRAIN_NEURALNETWORK_H
#define SPARKAI_AI_BRAIN_NEURALNETWORK_H

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"
#include "TensorRef.h"

namespace SparkLabs {

class NeuralNetwork {
public:
    NeuralNetwork();
    virtual ~NeuralNetwork();

    virtual TensorRef Forward(const TensorRef& input) = 0;
    virtual void LoadModel(const String& path) = 0;
    virtual void SaveModel(const String& path) = 0;

    Vector<int32> GetInputShape() const { return m_InputShape; }
    Vector<int32> GetOutputShape() const { return m_OutputShape; }

    void SetInputShape(const Vector<int32>& shape) { m_InputShape = shape; }
    void SetOutputShape(const Vector<int32>& shape) { m_OutputShape = shape; }

    void SetInferenceMode(bool useGPU);
    bool IsUsingGPU() const { return m_UseGPU; }

    bool IsValid() const { return m_IsValid; }

protected:
    Vector<int32> m_InputShape;
    Vector<int32> m_OutputShape;
    bool m_UseGPU;
    bool m_IsValid;
};

}

#endif