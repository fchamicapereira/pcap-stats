#pragma once

#include "types.h"

#include <assert.h>
#include <optional>
#include <fstream>

constexpr const u16 ETHERTYPE_IP       = 0x0800; /* IP */
constexpr const u16 ETHERTYPE_ARP      = 0x0806; /* Address resolution */
constexpr const u16 ETHERTYPE_REVARP   = 0x8035; /* Reverse ARP */
constexpr const u16 ETHERTYPE_AT       = 0x809B; /* AppleTalk protocol */
constexpr const u16 ETHERTYPE_AARP     = 0x80F3; /* AppleTalk ARP */
constexpr const u16 ETHERTYPE_VLAN     = 0x8100; /* IEEE 802.1Q VLAN tagging */
constexpr const u16 ETHERTYPE_IPX      = 0x8137; /* IPX */
constexpr const u16 ETHERTYPE_IPV6     = 0x86dd; /* IP protocol version 6 */
constexpr const u16 ETHERTYPE_LOOPBACK = 0x9000; /* used to test interfaces */

constexpr const bytes_t CRC_SIZE_BYTES      = 4;
constexpr const bytes_t PREAMBLE_SIZE_BYTES = 8;
constexpr const bytes_t IPG_SIZE_BYTES      = 12;
constexpr const bytes_t MIN_PKT_SIZE_BYTES  = 64;
constexpr const bytes_t MAX_PKT_SIZE_BYTES  = 1500;

struct ether_addr_t {
  u8 addr_bytes[6];
} __attribute__((__packed__));

struct ether_hdr_t {
  ether_addr_t daddr;
  ether_addr_t saddr;
  u16 ether_type;
} __attribute__((__packed__));

struct ipv4_hdr_t {
  u8 ihl : 4;
  u8 version : 4;
  u8 type_of_service;
  u16 total_length;
  u16 packet_id;
  u16 fragment_offset;
  u8 time_to_live;
  u8 next_proto_id;
  u16 hdr_checksum;
  u32 src_addr;
  u32 dst_addr;
} __attribute__((__packed__));

struct udp_hdr_t {
  u16 src_port;
  u16 dst_port;
  u16 len;
  u16 checksum;
} __attribute__((__packed__));

struct tcp_hdr_t {
  u16 src_port;
  u16 dst_port;
  u32 sent_seq;
  u32 recv_ack;
  u8 data_off;
  u8 tcp_flags;
  u16 rx_win;
  u16 cksum;
  u16 tcp_urp;
} __attribute__((__packed__));

struct vlan_hdr_t {
  u16 vlan_tpid;
  u16 vlan_tci;
} __attribute__((__packed__));

inline std::string ipv4_to_str(u32 addr) {
  std::stringstream ss;
  ss << ((addr >> 0) & 0xff);
  ss << ".";
  ss << ((addr >> 8) & 0xff);
  ss << ".";
  ss << ((addr >> 16) & 0xff);
  ss << ".";
  ss << ((addr >> 24) & 0xff);
  return ss.str();
}

inline u32 ipv4_set_prefix(u32 addr, u8 prefix, bits_t prefix_size) {
  assert(prefix_size <= 32);
  const u32 swapped_addr  = bswap32(addr);
  const u32 mask          = (1ull << prefix_size) - 1;
  const u32 prefix_masked = prefix & mask;
  return bswap32((prefix_masked << (32 - prefix_size)) | (swapped_addr >> prefix_size));
}

enum class FlowType {
  FiveTuple = 0,
};

struct flow_t {
  FlowType type;

  union {
    struct {
      u32 src_ip;
      u32 dst_ip;
      u16 src_port;
      u16 dst_port;
    } five_tuple;
  };

  flow_t() : type(FlowType::FiveTuple), five_tuple({.src_ip = 0, .dst_ip = 0, .src_port = 0, .dst_port = 0}) {}

  flow_t(const flow_t &flow) {
    type = flow.type;
    switch (flow.type) {
    case FlowType::FiveTuple:
      five_tuple.src_ip   = flow.five_tuple.src_ip;
      five_tuple.dst_ip   = flow.five_tuple.dst_ip;
      five_tuple.src_port = flow.five_tuple.src_port;
      five_tuple.dst_port = flow.five_tuple.dst_port;
      break;
    }
  }

  flow_t &operator=(const flow_t &flow) {
    if (this == &flow) {
      return *this;
    }

    type = flow.type;

    switch (flow.type) {
    case FlowType::FiveTuple:
      five_tuple.src_ip   = flow.five_tuple.src_ip;
      five_tuple.dst_ip   = flow.five_tuple.dst_ip;
      five_tuple.src_port = flow.five_tuple.src_port;
      five_tuple.dst_port = flow.five_tuple.dst_port;
      break;
    }

    return *this;
  }

  flow_t invert() const {
    assert(type == FlowType::FiveTuple);
    flow_t inverted;
    inverted.type                = FlowType::FiveTuple;
    inverted.five_tuple.src_ip   = five_tuple.dst_ip;
    inverted.five_tuple.dst_ip   = five_tuple.src_ip;
    inverted.five_tuple.src_port = five_tuple.dst_port;
    inverted.five_tuple.dst_port = five_tuple.src_port;
    return inverted;
  }

  bool operator==(const flow_t &other) const {
    if (type != other.type) {
      return false;
    }

    switch (type) {
    case FlowType::FiveTuple:
      return five_tuple.src_ip == other.five_tuple.src_ip && five_tuple.dst_ip == other.five_tuple.dst_ip &&
             five_tuple.src_port == other.five_tuple.src_port && five_tuple.dst_port == other.five_tuple.dst_port;
    }

    return false;
  }

  struct flow_hash_t {
    std::size_t operator()(const flow_t &flow) const {
      std::size_t hash = 0;
      switch (flow.type) {
      case FlowType::FiveTuple: {
        hash = std::hash<u32>()(flow.five_tuple.src_ip);
        hash ^= std::hash<u32>()(flow.five_tuple.dst_ip);
        hash ^= std::hash<u16>()(flow.five_tuple.src_port);
        hash ^= std::hash<u16>()(flow.five_tuple.dst_port);
      } break;
      }
      return hash;
    }
  };
};

inline std::ostream &operator<<(std::ostream &os, const flow_t &flow) {
  os << "{";

  switch (flow.type) {
  case FlowType::FiveTuple:
    os << ipv4_to_str(flow.five_tuple.src_ip);
    os << ":";
    os << bswap16(flow.five_tuple.src_port);

    os << " -> ";

    os << ipv4_to_str(flow.five_tuple.dst_ip);
    os << ":";
    os << bswap16(flow.five_tuple.dst_port);
    break;
  }

  os << "}";
  return os;
}

// Symmetric
struct sflow_t {
  u32 src_ip;
  u32 dst_ip;
  u16 src_port;
  u16 dst_port;

  sflow_t() : src_ip(0), dst_ip(0), src_port(0), dst_port(0) {}

  sflow_t(const flow_t &flow)
      : src_ip(flow.five_tuple.src_ip), dst_ip(flow.five_tuple.dst_ip), src_port(flow.five_tuple.src_port), dst_port(flow.five_tuple.dst_port) {}

  sflow_t(const sflow_t &sflow) : src_ip(sflow.src_ip), dst_ip(sflow.dst_ip), src_port(sflow.src_port), dst_port(sflow.dst_port) {}

  sflow_t(u32 _src_ip, u32 _dst_ip, u16 _src_port, u16 _dst_port) : src_ip(_src_ip), dst_ip(_dst_ip), src_port(_src_port), dst_port(_dst_port) {}

  bool operator==(const sflow_t &other) const {
    return (src_ip == other.src_ip && dst_ip == other.dst_ip && src_port == other.src_port && dst_port == other.dst_port) ||
           (src_ip == other.dst_ip && dst_ip == other.src_ip && src_port == other.dst_port && dst_port == other.src_port);
  }

  struct flow_hash_t {
    std::size_t operator()(const sflow_t &sflow) const {
      return std::hash<u32>()(sflow.src_ip) ^ std::hash<u32>()(sflow.dst_ip) ^ std::hash<u16>()(sflow.src_port) ^ std::hash<u16>()(sflow.dst_port);
    }
  };
};

struct packet_t {
  const u8 *pkt;
  u16 hdrs_len;
  u16 total_len;
  time_ns_t ts;
  std::optional<flow_t> flow;
};
