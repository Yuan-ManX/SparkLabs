#include "FileStream.h"

namespace SparkLabs {

FileStream::FileStream(std::FILE* file, bool writable)
    : m_File(file), m_Writable(writable) {
}

FileStream::~FileStream() {
    Close();
}

size_t FileStream::Read(void* buffer, size_t size) {
    if (!m_File || !buffer || size == 0) {
        return 0;
    }
    return std::fread(buffer, 1, size, m_File);
}

size_t FileStream::Write(const void* buffer, size_t size) {
    if (!m_File || !m_Writable || !buffer || size == 0) {
        return 0;
    }
    return std::fwrite(buffer, 1, size, m_File);
}

void FileStream::Seek(int64 offset, int32 origin) {
    if (!m_File) {
        return;
    }
#if defined(_WIN32) || defined(_WIN64)
    _fseeki64(m_File, offset, origin);
#else
    fseeko(m_File, static_cast<off_t>(offset), origin);
#endif
}

int64 FileStream::Tell() const {
    if (!m_File) {
        return 0;
    }
#if defined(_WIN32) || defined(_WIN64)
    return _ftelli64(m_File);
#else
    return static_cast<int64>(ftello(m_File));
#endif
}

bool FileStream::IsEOF() const {
    if (!m_File) {
        return true;
    }
    return std::feof(m_File) != 0;
}

void FileStream::Flush() {
    if (m_File && m_Writable) {
        std::fflush(m_File);
    }
}

void FileStream::Close() {
    if (m_File) {
        std::fclose(m_File);
        m_File = nullptr;
    }
}

}
