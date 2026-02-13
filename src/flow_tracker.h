#pragma once

#include "double_chain.h"
#include "types.h"
#include "net.h"

#include <unordered_map>

class FlowTracker {
  DoubleChain double_chain;
  std::unordered_map<flow_t, u64, flow_t::flow_hash_t> flow_to_index;
  std::vector<flow_t> index_to_flow;

public:
  FlowTracker(u64 capacity);

  bool has_flow(const flow_t &flow) const;
  void add_flow(const flow_t &flow, time_ns_t now);
  u64 expire_flows(time_ns_t now);
};