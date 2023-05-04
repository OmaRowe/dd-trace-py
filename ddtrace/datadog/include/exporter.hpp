// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0. This product includes software
// developed at Datadog (https://www.datadoghq.com/). Copyright 2021-Present
// Datadog, Inc.
#pragma once

#include <array>
#include <chrono>
#include <string>
#include <string_view>
#include <memory>
#include <vector>
#include <unordered_set>
#include <unordered_map>

extern "C" {
#include "datadog/profiling.h"
}

namespace Datadog {

// Forward
class Profile;
class Uploader;

// There's currently no need to offer custom tags, so there's no interface for
// it.  Instead, tags are keyed and populated based on this table, then
// referenced in `add_tag()`.
// There are two columns because runtime-id has a dash.
#define EXPORTER_TAGS(X) \
  X(language,         "language") \
  X(env,              "env") \
  X(service,          "service") \
  X(version,          "version") \
  X(runtime_version,  "runtime_version") \
  X(runtime,          "runtime") \
  X(runtime_id,       "runtime-id") \
  X(profiler_version, "profiler_version") \
  X(profile_seq,      "profile_seq")

#define EXPORTER_LABELS(X) \
  X(exception_type,           "exception type") \
  X(thread_id,                "thread id") \
  X(thread_native_id,         "thread native id") \
  X(thread_name,              "thread name") \
  X(task_id,                  "task id") \
  X(task_name,                "task name") \
  X(span_id,                  "span id") \
  X(local_root_span_id,       "local root span id") \
  X(trace_type,               "trace type") \
  X(trace_resource_container, "trace resource container") \
  X(trace_endpoint,           "trace endpoint") \
  X(class_name,               "class name") \
  X(lock_name,                "lock name")

#define X_ENUM(a, b) a,
enum class ExportTagKey {
  EXPORTER_TAGS(X_ENUM)
  _Length
};

enum class ExportLabelKey {
  EXPORTER_LABELS(X_ENUM)
  _Length
};
#undef X_ENUM

// This is a wrapper class over a ddog_prof_Exporter object, which is part of
// libdatadog.  It manages the lifetime and initialization of that object.
// It is intended to be used only by Uploader
class DdogProfExporter {
private:
  using ExporterTagset = std::unordered_map<std::string_view, std::string_view>;
  friend class UploaderBuilder;
  friend class Uploader;

  void add_tag(ddog_Vec_Tag &tags, const ExportTagKey key, std::string_view val);
  void add_tag_unsafe(ddog_Vec_Tag &tags, std::string_view key, std::string_view val);

  static constexpr std::string_view language = "python";
  static constexpr std::string_view family = "python";
  
public:
  DdogProfExporter(std::string_view env,
                   std::string_view service,
                   std::string_view version,
                   std::string_view runtime,
                   std::string_view runtime_version,
                   std::string_view profiler_version,
                   std::string_view url,
                   ExporterTagset &user_tags);
  ~DdogProfExporter();

  ddog_prof_Exporter *ptr;
};

class Uploader {
  bool agentless; // Whether or not to actually use API key/intake
  size_t profile_seq = 0;
  std::string runtime_id;
  std::string url;

  std::unique_ptr<DdogProfExporter> ddog_exporter;

public:

  Uploader(std::string_view _env,
           std::string_view _service,
           std::string_view _version,
           std::string_view _runtime,
           std::string_view _runtime_version,
           std::string_view _profiler_version,
           std::string_view _url,
           DdogProfExporter::ExporterTagset &user_tags);
  void set_runtime_id(const std::string &id);
  bool upload(const Profile *profile);

};

class UploaderBuilder {
  std::string env;
  std::string service;
  std::string version;
  std::string runtime;
  std::string runtime_version;
  std::string profiler_version;
  std::string url;
  DdogProfExporter::ExporterTagset user_tags;

public:
  UploaderBuilder &set_env(std::string_view env);
  UploaderBuilder &set_service(std::string_view service);
  UploaderBuilder &set_version(std::string_view version);
  UploaderBuilder &set_runtime(std::string_view runtime);
  UploaderBuilder &set_runtime_version(std::string_view runtime_version);
  UploaderBuilder &set_profiler_version(std::string_view profiler_version);
  UploaderBuilder &set_url(std::string_view url);
  UploaderBuilder &set_tag(std::string_view key, std::string_view val);

  UploaderBuilder(std::string_view _env = "prod",
                  std::string_view _service = "py_libdatadog",
                  std::string_view _version = "",
                  std::string_view _runtime = "cython",
                  std::string_view _runtime_version = "???",
                  std::string_view _profiler_version = "???",
                  std::string_view _url = "http://localhost:8126");

  Uploader *build_ptr();
};

class Profile {
public:
  enum ProfileType : unsigned int {
    CPU         = 1<<0,
    Wall        = 1<<1,
    Exception   = 1<<2,
    LockAcquire = 1<<3,
    LockRelease = 1<<4,
    Allocation  = 1<<5,
    Heap        = 1<<6,
    All = CPU | Wall | Exception | LockAcquire | LockRelease | Allocation | Heap
  };

private:
  unsigned int type_mask;
  unsigned int max_nframes;
  unsigned int nframes;

  // Keeps temporary buffer of frames in the stack
  std::vector<ddog_prof_Location> locations;
  std::vector<ddog_prof_Line> lines;

  // Storage for strings
  std::unordered_set<std::string> strings;

  // Storage for labels
  ddog_prof_Label labels[8];
  size_t cur_label = 0;
  
  // Storage for values
  std::vector<int64_t> values = {};
  struct {
    unsigned short cpu_time;
    unsigned short cpu_count;
    unsigned short wall_time;
    unsigned short wall_count;
    unsigned short exception_count;
    unsigned short lock_acquire_time;
    unsigned short lock_acquire_count;
    unsigned short lock_release_time;
    unsigned short lock_release_count;
    unsigned short alloc_space;
    unsigned short alloc_count;
    unsigned short heap_space;
  } val_idx;

  // Helpers
  void push_label(const ExportLabelKey key, std::string_view val);
  void push_label(const ExportLabelKey key, int64_t val);
  void push_frame_impl(
        std::string_view name,
        std::string_view filename,
        uint64_t address,
        int64_t line
      );

public:
  uint64_t samples = 0;
  ddog_prof_Profile *ddog_profile;

  // Clears the current sample without flushing and starts a new one
  void start_sample(unsigned int nframes);

  // Add values
  void push_walltime(int64_t walltime, int64_t count);
  void push_cputime(int64_t cputime, int64_t count);
  void push_acquire(int64_t acquire_time, int64_t count);
  void push_release(int64_t lock_time, int64_t count);
  void push_alloc(uint64_t size, uint64_t count);
  void push_heap(uint64_t size);

  // Adds metadata to sample
  void push_lock_name(std::string_view lock_name);
  void push_threadinfo(
        int64_t thread_id,
        int64_t thread_native_id,
        std::string_view thread_name
      );
  void push_taskinfo(
        int64_t task_id,
        std::string_view task_name
      );
  void push_span_id(int64_t span_id);
  void push_local_root_span_id(int64_t local_root_span_id);
  void push_trace_type(std::string_view trace_type);
  void push_trace_resource_container(std::string_view trace_resource_container);

  void push_exceptioninfo(
        std::string_view exception_type,
        int64_t count
      );

  void push_class_name(std::string_view class_name);

  // Assumes frames are pushed in leaf-order
  void push_frame(
        std::string_view name,      // for ddog_prof_Function
        std::string_view filename,  // for ddog_prof_Function
        uint64_t address,           // for ddog_prof_Location
        int64_t line                // for ddog_prof_Line
      );
    

  // Flushes the current buffer, clearing it
  bool flush_sample();

  // Clears temporary things
  void clear_buffers();

  // Zero out stats
  void zero_stats();

  void reset();
  Profile(ProfileType type, unsigned int _max_nframes = 64);
  ~Profile();
};

class ProfileBuilder {
  Profile::ProfileType type_mask;
  unsigned int max_nframes;

public:
  ProfileBuilder &add_type(Profile::ProfileType type);
  ProfileBuilder &add_type(unsigned int type);
  ProfileBuilder &set_max_nframes(unsigned int max_nframes);

  ProfileBuilder(Profile::ProfileType _type_mask = Profile::ProfileType::All,
                 unsigned int _max_nframes = 64);

  Profile *build_ptr();
};

} // namespace Datadog
