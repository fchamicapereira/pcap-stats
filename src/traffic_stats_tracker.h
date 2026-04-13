#pragma once

#include "types.h"
#include "pcap_reader.h"
#include "clock.h"
#include "cdf.h"
#include "flow_tracker.h"

#include <filesystem>
#include <vector>
#include <unordered_set>
#include <unordered_map>
#include <array>

static constexpr const size_t BATCH_SIZE = 32;

struct flow_ts {
  time_ns_t first;
  time_ns_t last;
  std::vector<time_ns_t> dts;
};

struct epoch_t {
  u64 expired_flows;
  u64 new_flows;
  u64 concurrent_flows;
};

struct report_t {
  time_ns_t start;
  time_ns_t end;
  u64 total_pkts;
  u64 total_bytes;
  u64 tcpudp_pkts;
  CDF pkt_sizes_cdf;
  u64 total_flows;
  u64 total_symm_flows;
  CDF concurrent_flows_per_epoch;
  CDF pkts_per_flow_cdf;
  CDF top_k_flows_cdf;
  CDF top_k_flows_bytes_cdf;
  CDF flow_duration_us_cdf;
  CDF flow_dts_us_cdf;
  std::map<double, flow_t> relative_pkts_per_flow;
  std::vector<epoch_t> epochs;

  std::array<u64, 32> batch32_stride_sizes_unsorted;
  std::array<u64, 32> batch32_stride_sizes_sorted;

  std::array<u64, 64> batch64_stride_sizes_unsorted;
  std::array<u64, 64> batch64_stride_sizes_sorted;

  std::array<u64, 128> batch128_stride_sizes_unsorted;
  std::array<u64, 128> batch128_stride_sizes_sorted;

  report_t()
      : start(0), end(0), total_pkts(0), tcpudp_pkts(0), total_flows(0), total_symm_flows(0), batch32_stride_sizes_unsorted({}),
        batch32_stride_sizes_sorted({}), batch64_stride_sizes_unsorted({}), batch64_stride_sizes_sorted({}), batch128_stride_sizes_unsorted({}),
        batch128_stride_sizes_sorted({}) {}
};

struct traffic_stats_tracker_t {
  simulator_clock_t clock;

  std::unordered_set<flow_t, flow_t::flow_hash_t> flows;
  std::unordered_set<sflow_t, sflow_t::flow_hash_t> symm_flows;
  std::vector<std::unordered_set<flow_t, flow_t::flow_hash_t>> concurrent_flows_per_epoch;
  std::vector<u64> expired_flows_per_epoch;
  std::vector<u64> new_flows_per_epoch;
  FlowTracker flow_tracker;
  std::unordered_map<flow_t, u64, sflow_t::flow_hash_t> pkts_per_flow;
  std::unordered_map<flow_t, u64, sflow_t::flow_hash_t> bytes_per_flow;
  std::unordered_map<flow_t, flow_ts, sflow_t::flow_hash_t> flow_times;
  std::vector<std::optional<flow_t>> batch32;
  std::vector<std::optional<flow_t>> batch64;
  std::vector<std::optional<flow_t>> batch128;

  report_t report;

  traffic_stats_tracker_t(time_ns_t _epoch_duration) : clock(_epoch_duration), flow_tracker(100'000'000) {
    concurrent_flows_per_epoch.emplace_back();
    expired_flows_per_epoch.emplace_back();
    new_flows_per_epoch.emplace_back();
  }

  void feed_packet(const packet_t &pkt);
  void generate_report();
  void dump_report_to_json_file(const std::filesystem::path &json_output_report) const;

  static void sort_batch(std::vector<std::optional<flow_t>> &batch);

  template <size_t BATCH_SIZE> static void process_batch(const std::vector<std::optional<flow_t>> &batch, std::array<u64, BATCH_SIZE> &stride_sizes) {
    assert(batch.size() == BATCH_SIZE);
    std::vector<u8> strides;
    strides.push_back(1);

    for (u8 i = 0; i < BATCH_SIZE - 1; i++) {
      if (batch[i].has_value() == batch[i + 1].has_value() && (!batch[i].has_value() || batch[i].value() == batch[i + 1].value())) {
        strides.back()++;
      } else {
        strides.push_back(1);
      }
    }

    for (u8 stride : strides) {
      stride_sizes[stride - 1]++;
    }
  }
};