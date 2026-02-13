#include <CLI/CLI.hpp>

#include "pcap_reader.h"
#include "traffic_stats_tracker.h"
#include "system.h"

#include <iostream>
#include <filesystem>

constexpr const time_ns_t DEFAULT_EPOCH_DURATION_NS = 1'000'000'000; // 1 second in nanoseconds

struct args_t {
  std::filesystem::path pcap_file;
  std::filesystem::path output_report;
  time_ns_t epoch_duration;
  std::optional<Mbps_t> rate;

  args_t() : epoch_duration(DEFAULT_EPOCH_DURATION_NS) {}
};

int main(int argc, char **argv) {
  args_t args;

  CLI::App app{"Pcap stats"};
  app.add_option("pcap", args.pcap_file, "Pcap file.")->required();
  app.add_option("--out", args.output_report, "Output report JSON file.");
  app.add_option("--epoch", args.epoch_duration, "Epoch duration in nanoseconds (default: 1s).");
  app.add_option("--mbps", args.rate, "Replay rate in Mbps (optional).");

  CLI11_PARSE(app, argc, argv);

  if (!std::filesystem::exists(args.pcap_file)) {
    fprintf(stderr, "File %s not found\n", args.pcap_file.c_str());
    exit(1);
  }

  traffic_stats_tracker_t traffic_stats_tracker(args.epoch_duration);

  while (traffic_stats_tracker.report.end - traffic_stats_tracker.report.start < traffic_stats_tracker.clock.epoch_duration) {
    const time_ns_t base_time = traffic_stats_tracker.report.end - traffic_stats_tracker.report.start;
    time_ns_t current_time    = base_time;

    pcap_reader_t reader(args.pcap_file);
    packet_t packet;
    while (reader.read_next_packet(packet)) {
      if (current_time == 0) {
        current_time = packet.ts;
      }

      if (args.rate.has_value()) {
        const bits_t bits_in_wire   = (PREAMBLE_SIZE_BYTES + IPG_SIZE_BYTES + packet.total_len) * 8;
        const time_ns_t pkt_time_ns = (THOUSAND * bits_in_wire) / static_cast<double>(args.rate.value());
        current_time += pkt_time_ns;
      } else {
        current_time = base_time + packet.ts;
      }

      packet.ts = current_time;
      traffic_stats_tracker.feed_packet(packet);
    }

    const time_ns_t elapsed_ns = traffic_stats_tracker.report.end - traffic_stats_tracker.report.start;

    std::cerr << "pkts:    " << traffic_stats_tracker.report.total_pkts << "\n";
    std::cerr << "start:   " << traffic_stats_tracker.report.start << "\n";
    std::cerr << "end:     " << traffic_stats_tracker.report.end << "\n";
    std::cerr << "elapsed: " << elapsed_ns << " ns (" << (elapsed_ns / static_cast<double>(BILLION)) << " s)\n";
  }

  traffic_stats_tracker.generate_report();
  if (!args.output_report.empty()) {
    traffic_stats_tracker.dump_report_to_json_file(args.output_report);
  }

  return 0;
}