#include "FileSystem.h"
#include "FileStream.h"
#include <fstream>
#include <sstream>
#include <filesystem>

namespace SparkLabs {

FileSystem* FileSystem::s_Instance = nullptr;

FileSystem* FileSystem::GetInstance() {
    return s_Instance;
}

void FileSystem::SetInstance(FileSystem* instance) {
    s_Instance = instance;
}

bool FileSystem::Exists(const String& path) const {
    return std::filesystem::exists(path.C_str());
}

bool FileSystem::IsDirectory(const String& path) const {
    return std::filesystem::is_directory(path.C_str());
}

bool FileSystem::CreateDirectory(const String& path) {
    return std::filesystem::create_directories(path.C_str());
}

bool FileSystem::Delete(const String& path) {
    if (IsDirectory(path)) {
        return std::filesystem::remove_all(path.C_str()) > 0;
    }
    return std::filesystem::remove(path.C_str());
}

bool FileSystem::Copy(const String& from, const String& to) {
    try {
        std::filesystem::copy(from.C_str(), to.C_str());
        return true;
    } catch (...) {
        return false;
    }
}

String FileSystem::ReadAllText(const String& path) {
    std::ifstream file(path.C_str());
    if (!file.is_open()) {
        return String();
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return String(buffer.str().c_str());
}

Vector<uint8_t> FileSystem::ReadAllBytes(const String& path) {
    Vector<uint8_t> result;
    std::ifstream file(path.C_str(), std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        return result;
    }
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    result.Resize(static_cast<size_t>(size));
    file.read(reinterpret_cast<char*>(result.Data()), size);
    return result;
}

void FileSystem::WriteAllText(const String& path, const String& content) {
    std::ofstream file(path.C_str());
    if (file.is_open()) {
        file << content.C_str();
        file.close();
    }
}

void FileSystem::WriteAllBytes(const String& path, const Vector<uint8_t>& data) {
    std::ofstream file(path.C_str(), std::ios::binary);
    if (file.is_open()) {
        file.write(reinterpret_cast<const char*>(data.Data()), static_cast<std::streamsize>(data.Size()));
        file.close();
    }
}

Vector<String> FileSystem::ListFiles(const String& path, const String& pattern) {
    Vector<String> result;
    try {
        for (const auto& entry : std::filesystem::directory_iterator(path.C_str())) {
            if (entry.is_regular_file()) {
                String filename = entry.path().filename().string().c_str();
                if (pattern == "*" || filename.Find(pattern) != -1) {
                    result.PushBack(entry.path().string().c_str());
                }
            }
        }
    } catch (...) {
    }
    return result;
}

FileStream* FileSystem::OpenFile(const String& path, FileMode mode) {
    std::ios_base::openmode openMode;
    switch (mode) {
        case FileMode::Read:
            openMode = std::ios::in | std::ios::binary;
            break;
        case FileMode::Write:
            openMode = std::ios::out | std::ios::binary | std::ios::trunc;
            break;
        case FileMode::Append:
            openMode = std::ios::out | std::ios::binary | std::ios::app;
            break;
        default:
            openMode = std::ios::in | std::ios::binary;
            break;
    }

    std::FILE* file = std::fopen(path.C_str(),
        mode == FileMode::Read ? "rb" :
        mode == FileMode::Write ? "wb" : "ab");

    if (!file) {
        return nullptr;
    }

    return new FileStream(file, mode == FileMode::Write || mode == FileMode::Append);
}

}
