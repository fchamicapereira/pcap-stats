#include "traffic_stats_tracker.h"
#include "system.h"

#include <nlohmann/json.hpp>
#include <fstream>

using json = nlohmann::json;

constexpr const u64 TRAFFIC_STATS_TRACKER_PROGRESS_PRINT_STEP = 1'000'000;

void traffic_stats_tracker_t::feed_packet(const packet_t &pkt) {
  if (report.total_pkts % TRAFFIC_STATS_TRACKER_PROGRESS_PRINT_STEP == 0) {
    std::cerr << "[" << pkt.ts << "] Processed " << report.total_pkts << " packets..." << std::endl;
  }

  report.end = pkt.ts;
  if (report.start == 0) {
    report.start = pkt.ts;
  }

  report.total_pkts++;
  report.total_bytes += pkt.total_len;
  report.pkt_sizes_cdf.add(pkt.total_len);

  if (clock.tick(pkt.ts)) {
    concurrent_flows_per_epoch.emplace_back();
    expired_flows_per_epoch.emplace_back();
    new_flows_per_epoch.emplace_back();
  }

  batch32.push_back(pkt.flow);
  batch64.push_back(pkt.flow);
  batch128.push_back(pkt.flow);

  if (batch32.size() == 32) {
    process_batch(batch32, report.batch32_stride_sizes_unsorted);
    sort_batch(batch32);
    process_batch(batch32, report.batch32_stride_sizes_sorted);
    batch32.clear();
  }

  if (batch64.size() == 64) {
    process_batch(batch64, report.batch64_stride_sizes_unsorted);
    sort_batch(batch64);
    process_batch(batch64, report.batch64_stride_sizes_sorted);
    batch64.clear();
  }

  if (batch128.size() == 128) {
    process_batch(batch128, report.batch128_stride_sizes_unsorted);
    sort_batch(batch128);
    process_batch(batch128, report.batch128_stride_sizes_sorted);
    batch128.clear();
  }

  if (!pkt.flow.has_value()) {
    return;
  }

  expired_flows_per_epoch.back() += flow_tracker.expire_flows(pkt.ts);
  if (!flow_tracker.has_flow(pkt.flow.value())) {
    flow_tracker.add_flow(pkt.flow.value(), pkt.ts);
    new_flows_per_epoch.back()++;
  }

  report.tcpudp_pkts++;
  flows.insert(pkt.flow.value());
  symm_flows.insert(pkt.flow.value());
  concurrent_flows_per_epoch.back().insert(pkt.flow.value());
  pkts_per_flow[pkt.flow.value()]++;
  bytes_per_flow[pkt.flow.value()] += pkt.total_len;

  auto flow_times_it = flow_times.find(pkt.flow.value());

  if (flow_times_it == flow_times.end()) {
    flow_times[pkt.flow.value()] = {
        .first = pkt.ts,
        .last  = pkt.ts,
        .dts   = {},
    };
  } else {
    flow_ts &fts       = flow_times_it->second;
    const time_ns_t dt = pkt.ts - fts.last;
    fts.last           = pkt.ts;
    fts.dts.push_back(dt);
  }
}

void traffic_stats_tracker_t::generate_report() {
  report.total_flows      = flows.size();
  report.total_symm_flows = symm_flows.size();

  for (const auto &flows : concurrent_flows_per_epoch) {
    report.concurrent_flows_per_epoch.add(flows.size());
  }

  for (size_t i = 0; i < expired_flows_per_epoch.size(); i++) {
    report.epochs.push_back({
        .expired_flows    = expired_flows_per_epoch[i],
        .new_flows        = new_flows_per_epoch[i],
        .concurrent_flows = concurrent_flows_per_epoch[i].size(),
    });
  }

  std::vector<u64> pkts_per_flow_values;
  std::vector<u64> bytes_per_flow_values;

  for (const auto &[flow, pkts] : pkts_per_flow) {
    report.pkts_per_flow_cdf.add(pkts);
    pkts_per_flow_values.push_back(pkts);
    report.relative_pkts_per_flow[static_cast<double>(pkts) / report.total_pkts] = flow;
  }

  for (const auto &[flow, bytes] : bytes_per_flow) {
    bytes_per_flow_values.push_back(bytes);
  }

  assert(pkts_per_flow_values.size() == bytes_per_flow_values.size());

  std::sort(pkts_per_flow_values.begin(), pkts_per_flow_values.end(), std::greater<u64>());
  std::sort(bytes_per_flow_values.begin(), bytes_per_flow_values.end(), std::greater<u64>());

  for (size_t i = 0; i < pkts_per_flow_values.size(); i++) {
    report.top_k_flows_cdf.add(i + 1, pkts_per_flow_values[i]);
    report.top_k_flows_bytes_cdf.add(i + 1, bytes_per_flow_values[i]);
  }

  for (const auto &[flow, ts] : flow_times) {
    report.flow_duration_us_cdf.add((ts.last - ts.first) / THOUSAND);

    if (ts.dts.empty()) {
      continue;
    }

    time_us_t dt_sum = 0;
    for (const auto &dt : ts.dts) {
      dt_sum += dt / THOUSAND;
    }
    report.flow_dts_us_cdf.add(dt_sum / (double)ts.dts.size());
  }
}

void traffic_stats_tracker_t::dump_report_to_json_file(const std::filesystem::path &json_output_report) const {
  json j;
  j["start_utc_ns"]                   = report.start;
  j["end_utc_ns"]                     = report.end;
  j["total_pkts"]                     = report.total_pkts;
  j["total_bytes"]                    = report.total_bytes;
  j["tcpudp_pkts"]                    = report.tcpudp_pkts;
  j["pkt_bytes_avg"]                  = report.pkt_sizes_cdf.get_avg();
  j["pkt_bytes_stdev"]                = report.pkt_sizes_cdf.get_stdev();
  j["pkt_bytes_cdf"]                  = json();
  j["pkt_bytes_cdf"]["values"]        = json::array();
  j["pkt_bytes_cdf"]["probabilities"] = json::array();
  for (const auto &[v, p] : report.pkt_sizes_cdf.get_cdf()) {
    j["pkt_bytes_cdf"]["values"].push_back(v);
    j["pkt_bytes_cdf"]["probabilities"].push_back(p);
  }
  j["total_flows"]         = report.total_flows;
  j["total_symm_flows"]    = report.total_symm_flows;
  j["pkts_per_flow_avg"]   = report.pkts_per_flow_cdf.get_avg();
  j["pkts_per_flow_stdev"] = report.pkts_per_flow_cdf.get_stdev();
  j["pkts_per_flow"]       = json::array();
  // Reverse iteration to list flows in descending order of packet count.
  for (auto it = report.relative_pkts_per_flow.rbegin(); it != report.relative_pkts_per_flow.rend(); ++it) {
    const auto &[p, flow] = *it;
    json jflow;
    jflow["p"]    = p;
    jflow["flow"] = flow.to_string();
    j["pkts_per_flow"].push_back(jflow);
  }
  j["pkts_per_flow_cdf"]                  = json();
  j["pkts_per_flow_cdf"]["values"]        = json::array();
  j["pkts_per_flow_cdf"]["probabilities"] = json::array();
  for (const auto &[v, p] : report.pkts_per_flow_cdf.get_cdf()) {
    j["pkts_per_flow_cdf"]["values"].push_back(v);
    j["pkts_per_flow_cdf"]["probabilities"].push_back(p);
  }
  j["flow_duration_us_avg"]                  = report.flow_duration_us_cdf.get_avg();
  j["flow_duration_us_stdev"]                = report.flow_duration_us_cdf.get_stdev();
  j["flow_duration_us_cdf"]                  = json();
  j["flow_duration_us_cdf"]["values"]        = json::array();
  j["flow_duration_us_cdf"]["probabilities"] = json::array();
  for (const auto &[v, p] : report.flow_duration_us_cdf.get_cdf()) {
    j["flow_duration_us_cdf"]["values"].push_back(v);
    j["flow_duration_us_cdf"]["probabilities"].push_back(p);
  }
  j["flow_dts_us_avg"]                  = report.flow_dts_us_cdf.get_avg();
  j["flow_dts_us_stdev"]                = report.flow_dts_us_cdf.get_stdev();
  j["flow_dts_us_cdf"]                  = json();
  j["flow_dts_us_cdf"]["values"]        = json::array();
  j["flow_dts_us_cdf"]["probabilities"] = json::array();
  for (const auto &[v, p] : report.flow_dts_us_cdf.get_cdf()) {
    j["flow_dts_us_cdf"]["values"].push_back(v);
    j["flow_dts_us_cdf"]["probabilities"].push_back(p);
  }
  j["top_k_flows_cdf"]                  = json();
  j["top_k_flows_cdf"]["values"]        = json::array();
  j["top_k_flows_cdf"]["probabilities"] = json::array();
  for (const auto &[v, p] : report.top_k_flows_cdf.get_cdf()) {
    j["top_k_flows_cdf"]["values"].push_back(v);
    j["top_k_flows_cdf"]["probabilities"].push_back(p);
  }
  j["top_k_flows_bytes_cdf"]                  = json();
  j["top_k_flows_bytes_cdf"]["values"]        = json::array();
  j["top_k_flows_bytes_cdf"]["probabilities"] = json::array();
  for (const auto &[v, p] : report.top_k_flows_bytes_cdf.get_cdf()) {
    j["top_k_flows_bytes_cdf"]["values"].push_back(v);
    j["top_k_flows_bytes_cdf"]["probabilities"].push_back(p);
  }
  j["epochs"] = json::array();
  for (const auto &epoch : report.epochs) {
    json je;
    je["expired_flows"]    = epoch.expired_flows;
    je["new_flows"]        = epoch.new_flows;
    je["concurrent_flows"] = epoch.concurrent_flows;
    j["epochs"].push_back(je);
  }
  j["stride_sizes_per_batch"] = json();

  j["stride_sizes_per_batch"]["32"]             = json();
  j["stride_sizes_per_batch"]["32"]["unsorted"] = json::array();
  j["stride_sizes_per_batch"]["32"]["sorted"]   = json::array();
  for (size_t i = 0; i < 32; i++) {
    j["stride_sizes_per_batch"]["32"]["unsorted"].push_back(report.batch32_stride_sizes_unsorted[i]);
    j["stride_sizes_per_batch"]["32"]["sorted"].push_back(report.batch32_stride_sizes_sorted[i]);
  }

  j["stride_sizes_per_batch"]["64"]             = json();
  j["stride_sizes_per_batch"]["64"]["unsorted"] = json::array();
  j["stride_sizes_per_batch"]["64"]["sorted"]   = json::array();
  for (size_t i = 0; i < 64; i++) {
    j["stride_sizes_per_batch"]["64"]["unsorted"].push_back(report.batch64_stride_sizes_unsorted[i]);
    j["stride_sizes_per_batch"]["64"]["sorted"].push_back(report.batch64_stride_sizes_sorted[i]);
  }

  j["stride_sizes_per_batch"]["128"]             = json();
  j["stride_sizes_per_batch"]["128"]["unsorted"] = json::array();
  j["stride_sizes_per_batch"]["128"]["sorted"]   = json::array();
  for (size_t i = 0; i < 128; i++) {
    j["stride_sizes_per_batch"]["128"]["unsorted"].push_back(report.batch128_stride_sizes_unsorted[i]);
    j["stride_sizes_per_batch"]["128"]["sorted"].push_back(report.batch128_stride_sizes_sorted[i]);
  }

  fprintf(stderr, "\n");
  fprintf(stderr, "Dumping report to %s\n", json_output_report.c_str());

  std::ofstream out(json_output_report);
  out << j.dump(2) << std::endl;
}

void traffic_stats_tracker_t::sort_batch(std::vector<std::optional<flow_t>> &batch) {
  assert(batch.size() == BATCH_SIZE);
  std::sort(batch.begin(), batch.end(), [](const std::optional<flow_t> &a, const std::optional<flow_t> &b) {
    if (!a.has_value() && !b.has_value()) {
      return false;
    }
    if (!a.has_value()) {
      return false;
    }
    if (!b.has_value()) {
      return true;
    }
    const flow_t &fa = a.value();
    const flow_t &fb = b.value();
    if (fa.five_tuple.src_ip != fb.five_tuple.src_ip) {
      return fa.five_tuple.src_ip < fb.five_tuple.src_ip;
    }
    if (fa.five_tuple.dst_ip != fb.five_tuple.dst_ip) {
      return fa.five_tuple.dst_ip < fb.five_tuple.dst_ip;
    }
    if (fa.five_tuple.src_port != fb.five_tuple.src_port) {
      return fa.five_tuple.src_port < fb.five_tuple.src_port;
    }
    return fa.five_tuple.dst_port < fb.five_tuple.dst_port;
  });
}
