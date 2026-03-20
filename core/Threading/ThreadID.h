#pragma once

#include <atomic>

namespace SparkLabs {

    using ThreadID = uint32_t;

    inline ThreadID GetCurrentThreadID() {
        return static_cast<ThreadID>(reinterpret_cast<uintptr_t>(std::atomic_thread_fence(std::memory_order_seq_cst)));
    }

}