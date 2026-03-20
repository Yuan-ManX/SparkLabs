#include "AssetBrowser.h"
#include "AssetGeneratorPanel.h"
#include "../platform/FileSystem.h"

namespace SparkLabs {

AssetBrowser::AssetBrowser()
    : m_IsDragging(false) {
    m_GeneratorPanel = MakeSmartPtr<AssetGeneratorPanel>();
    m_CurrentPath = "/assets";
}

AssetBrowser::~AssetBrowser() {
}

void AssetBrowser::Refresh() {
    m_Assets.Clear();
    LoadAssetsFromDirectory(m_CurrentPath);
    m_FilteredAssets.Clear();
    if (m_Filter.Empty()) {
        m_FilteredAssets = m_Assets;
    } else {
        for (const auto& asset : m_Assets) {
            if (asset.name.Find(m_Filter) != -1 || asset.extension.Find(m_Filter) != -1) {
                m_FilteredAssets.PushBack(asset);
            }
        }
    }
}

void AssetBrowser::SetFilter(const String& filter) {
    m_Filter = filter;
    Refresh();
}

Vector<AssetItem> AssetBrowser::GetFilteredAssets() {
    return m_FilteredAssets;
}

void AssetBrowser::GenerateAssetPreview(const String& assetPath) {
}

void AssetBrowser::OnAssetDoubleClicked(const AssetItem& item) {
    switch (item.type) {
        case AssetItem::Type::Scene:
            break;
        case AssetItem::Type::Texture:
        case AssetItem::Type::Mesh:
        case AssetItem::Type::Material:
        case AssetItem::Type::Script:
        case AssetItem::Type::Audio:
        default:
            break;
    }
}

void AssetBrowser::OnAssetDragStarted(const AssetItem& item) {
    m_DraggedAsset = item;
    m_IsDragging = true;
}

void AssetBrowser::LoadAssetsFromDirectory(const String& path) {
    FileSystem* fs = FileSystem::GetInstance();
    if (!fs) {
        return;
    }

    Vector<String> files = fs->ListFiles(path);
    for (const auto& filePath : files) {
        AssetItem item;
        item.path = filePath;

        int32 lastSlash = filePath.Find_last_of("/\\");
        if (lastSlash >= 0) {
            item.name = filePath.Substring(lastSlash + 1);
        } else {
            item.name = filePath;
        }

        int32 dotPos = item.name.Find_last_of('.');
        if (dotPos >= 0) {
            item.extension = item.name.Substring(dotPos + 1);
        }

        item.type = GetAssetTypeFromExtension(item.extension);
        m_Assets.PushBack(item);
    }
}

AssetItem::Type AssetBrowser::GetAssetTypeFromExtension(const String& ext) {
    if (ext == "png" || ext == "jpg" || ext == "jpeg" || ext == "tga" || ext == "bmp") {
        return AssetItem::Type::Texture;
    }
    if (ext == "obj" || ext == "fbx" || ext == "gltf" || ext == "glb") {
        return AssetItem::Type::Mesh;
    }
    if (ext == "mat") {
        return AssetItem::Type::Material;
    }
    if (ext == "lua" || ext == "py" || ext == "cs") {
        return AssetItem::Type::Script;
    }
    if (ext == "scene") {
        return AssetItem::Type::Scene;
    }
    if (ext == "wav" || ext == "mp3" || ext == "ogg") {
        return AssetItem::Type::Audio;
    }
    return AssetItem::Type::Unknown;
}

void AssetBrowser::Update(float32 deltaTime) {
}

void AssetBrowser::Render() {
}

}
