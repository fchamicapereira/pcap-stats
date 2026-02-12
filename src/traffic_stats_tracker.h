#pragma once

#include "types.h"
#include "pcap_reader.h"
#include "clock.h"

#include <filesystem>
#include <vector>
#include <map>
#include <cmath>
#include <unordered_set>
#include <unordered_map>

class CDF {
private:
  std::unordered_map<u64, u64> values;
  u64 total;

public:
  CDF() : total(0) {}

  void add(u64 value) {
    values[value]++;
    total++;
  }

  void add(u64 value, u64 count) {
    values[value] += count;
    total += count;
  }

  std::unordered_map<u64, double> get_cdf() const {
    std::unordered_map<u64, double> cdf;
    u64 accounted = 0;

    double next_p = 0;
    double step   = 0.05;

    for (const auto &[value, count] : values) {
      accounted += count;

      if (accounted == total) {
        cdf[value] = 1;
        break;
      }

      double p = static_cast<double>(accounted) / total;

      if (p >= next_p) {
        cdf[value] = p;

        while (p >= next_p) {
          next_p += step;
        }
      }
    }

    return cdf;
  }

  double get_avg() const {
    double avg = 0;
    for (const auto &[value, count] : values) {
      avg += value * count;
    }
    return avg / total;
  }

  double get_stdev() const {
    double avg   = get_avg();
    double stdev = 0;
    for (const auto &[value, count] : values) {
      stdev += (value - avg) * (value - avg) * count;
    }
    return sqrt(stdev / total);
  }
};

struct flow_ts {
  time_ns_t first;
  time_ns_t last;
  std::vector<time_ns_t> dts;
};

struct report_t {
  time_ns_t start;
  time_ns_t end;
  u64 total_pkts;
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

  report_t() : start(0), end(0), total_pkts(0), tcpudp_pkts(0), total_flows(0), total_symm_flows(0) {}
};

struct traffic_stats_tracker_t {
  simulator_clock_t clock;

  std::unordered_set<flow_t, flow_t::flow_hash_t> flows;
  std::unordered_set<sflow_t, sflow_t::flow_hash_t> symm_flows;
  std::vector<std::unordered_set<flow_t, flow_t::flow_hash_t>> concurrent_flows_per_epoch;

  std::unordered_map<flow_t, u64, sflow_t::flow_hash_t> pkts_per_flow;
  std::unordered_map<flow_t, u64, sflow_t::flow_hash_t> bytes_per_flow;
  std::unordered_map<flow_t, flow_ts, sflow_t::flow_hash_t> flow_times;

  report_t report;

  traffic_stats_tracker_t(time_ns_t _epoch_duration) : clock(_epoch_duration) { concurrent_flows_per_epoch.emplace_back(); }

  void feed_packet(const packet_t &pkt);
  void generate_report();
  void dump_report_to_json_file(const std::filesystem::path &json_output_report) const;
};