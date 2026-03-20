#pragma once

#include "../core/Types.h"
#include <cstdio>

namespace SparkLabs {

class FileStream {
public:
    FileStream(std::FILE* file, bool writable);
    virtual ~FileStream();

    virtual size_t Read(void* buffer, size_t size);
    virtual size_t Write(const void* buffer, size_t size);
    virtual void Seek(int64 offset, int32 origin);
    virtual int64 Tell() const;
    virtual bool IsEOF() const;
    virtual void Flush();

    bool IsValid() const { return m_File != nullptr; }
    void Close();

private:
    std::FILE* m_File;
    bool m_Writable;
};

}
