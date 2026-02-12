#pragma once

#include "types.h"
#include "net.h"

#include <filesystem>
#include <optional>
#include <pcap.h>

struct pcap_reader_t {
  pcap_t *pd;
  bool assume_ip;
  long pcap_start;
  u64 total_pkts;
  time_ns_t start;
  time_ns_t end;

  pcap_reader_t(const std::filesystem::path &file);

  bool read_next_packet(packet_t &read_data);
};