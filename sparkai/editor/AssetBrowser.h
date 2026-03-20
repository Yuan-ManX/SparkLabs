#pragma once

#include "../core/Types.h"
#include "../core/string/String.h"
#include "../core/memory/SmartPtr.h"
#include "../core/io/Vector.h"

namespace SparkLabs {

class AssetGeneratorPanel;

struct AssetItem {
    String path;
    String name;
    String extension;
    int64 size;
    float64 modifiedTime;

    enum class Type { Unknown, Texture, Mesh, Material, Script, Scene, Audio };
    Type type;
};

class AssetBrowser {
public:
    AssetBrowser();
    ~AssetBrowser();

    void Refresh();
    void SetFilter(const String& filter);
    Vector<AssetItem> GetFilteredAssets();
    void GenerateAssetPreview(const String& assetPath);
    void OnAssetDoubleClicked(const AssetItem& item);
    void OnAssetDragStarted(const AssetItem& item);

    void Update(float32 deltaTime);
    void Render();

    SmartPtr<AssetGeneratorPanel> GetGeneratorPanel() const { return m_GeneratorPanel; }

private:
    void LoadAssetsFromDirectory(const String& path);
    AssetItem::Type GetAssetTypeFromExtension(const String& ext);

    String m_CurrentPath;
    String m_Filter;
    Vector<AssetItem> m_Assets;
    Vector<AssetItem> m_FilteredAssets;
    SmartPtr<AssetGeneratorPanel> m_GeneratorPanel;
    AssetItem m_DraggedAsset;
    bool m_IsDragging;
};

}
