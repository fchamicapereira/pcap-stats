#include <CLI/CLI.hpp>

#include "pcap_reader.h"
#include "traffic_stats_tracker.h"

#include <iostream>
#include <filesystem>

constexpr const time_ns_t DEFAULT_EPOCH_DURATION_NS = 1'000'000'000; // 1 second in nanoseconds

struct args_t {
  std::filesystem::path pcap_file;
  std::filesystem::path output_report;
  time_ns_t epoch_duration;

  args_t() : epoch_duration(DEFAULT_EPOCH_DURATION_NS) {}
};

int main(int argc, char **argv) {
  args_t args;

  CLI::App app{"Pcap stats"};
  app.add_option("pcap", args.pcap_file, "Pcap file.")->required();
  app.add_option("--out", args.output_report, "Output report JSON file.");
  app.add_option("--epoch", args.epoch_duration, "Epoch duration in nanoseconds (default: 1s).");

  CLI11_PARSE(app, argc, argv);

  if (!std::filesystem::exists(args.pcap_file)) {
    fprintf(stderr, "File %s not found\n", args.pcap_file.c_str());
    exit(1);
  }

  pcap_reader_t reader(args.pcap_file);
  traffic_stats_tracker_t traffic_stats_tracker(args.epoch_duration);

  packet_t packet;
  while (reader.read_next_packet(packet)) {
    traffic_stats_tracker.feed_packet(packet);
  }

  traffic_stats_tracker.generate_report();
  if (!args.output_report.empty()) {
    traffic_stats_tracker.dump_report_to_json_file(args.output_report);
  }

  return 0;
}