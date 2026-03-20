#pragma once

#include "../../core/Types.h"
#include "../../core/string/String.h"
#include "../../core/io/Vector.h"

namespace SparkLabs {

class FileStream;

class FileSystem {
public:
    FileSystem() = default;
    virtual ~FileSystem() = default;

    virtual bool Exists(const String& path) const;
    virtual bool IsDirectory(const String& path) const;
    virtual bool CreateDirectory(const String& path);
    virtual bool Delete(const String& path);
    virtual bool Copy(const String& from, const String& to);
    virtual String ReadAllText(const String& path);
    virtual Vector<uint8_t> ReadAllBytes(const String& path);
    virtual void WriteAllText(const String& path, const String& content);
    virtual void WriteAllBytes(const String& path, const Vector<uint8_t>& data);
    virtual Vector<String> ListFiles(const String& path, const String& pattern = "*");

    enum class FileMode { Read, Write, Append };
    FileStream* OpenFile(const String& path, FileMode mode);

    static FileSystem* GetInstance();
    static void SetInstance(FileSystem* instance);

private:
    static FileSystem* s_Instance;
};

}
