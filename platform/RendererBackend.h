#pragma once

#include "../render/RenderDevice.h"

namespace SparkLabs {

class MetalRenderBackend : public RenderDevice {
public:
    MetalRenderBackend();
    virtual ~MetalRenderBackend() override;

    virtual void Initialize(const RenderSettings& settings) override;
    virtual void Shutdown() override;
    virtual void BeginFrame() override;
    virtual void EndFrame() override;
    virtual void Draw(const DrawCall& call) override;
    virtual void SetViewport(int32 x, int32 y, int32 width, int32 height) override;
};

class VulkanRenderBackend : public RenderDevice {
public:
    VulkanRenderBackend();
    virtual ~VulkanRenderBackend() override;

    virtual void Initialize(const RenderSettings& settings) override;
    virtual void Shutdown() override;
    virtual void BeginFrame() override;
    virtual void EndFrame() override;
    virtual void Draw(const DrawCall& call) override;
    virtual void SetViewport(int32 x, int32 y, int32 width, int32 height) override;
};

class OpenGLRenderBackend : public RenderDevice {
public:
    OpenGLRenderBackend();
    virtual ~OpenGLRenderBackend() override;

    virtual void Initialize(const RenderSettings& settings) override;
    virtual void Shutdown() override;
    virtual void BeginFrame() override;
    virtual void EndFrame() override;
    virtual void Draw(const DrawCall& call) override;
    virtual void SetViewport(int32 x, int32 y, int32 width, int32 height) override;
};

class D3D11RenderBackend : public RenderDevice {
public:
    D3D11RenderBackend();
    virtual ~D3D11RenderBackend() override;

    virtual void Initialize(const RenderSettings& settings) override;
    virtual void Shutdown() override;
    virtual void BeginFrame() override;
    virtual void EndFrame() override;
    virtual void Draw(const DrawCall& call) override;
    virtual void SetViewport(int32 x, int32 y, int32 width, int32 height) override;
};

}
