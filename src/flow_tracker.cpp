#include "flow_tracker.h"
#include "system.h"

FlowTracker::FlowTracker(u64 capacity) : double_chain(capacity), flow_to_index(), index_to_flow(capacity) {}

u64 FlowTracker::expire_flows(time_ns_t now) {
  u64 expired_count = 0;
  u64 index_out;
  while (double_chain.expire_one_index(now, index_out)) {
    assert(index_out < index_to_flow.size());
    const flow_t &flow = index_to_flow.at(index_out);
    flow_to_index.erase(flow);
    expired_count++;
  }
  return expired_count;
}

bool FlowTracker::has_flow(const flow_t &flow) const { return flow_to_index.contains(flow); }

void FlowTracker::add_flow(const flow_t &flow, time_ns_t now) {
  if (has_flow(flow)) {
    return;
  }

  u64 index_out;
  if (!double_chain.allocate_new_index(now, index_out)) {
    panic("FlowTracker capacity exceeded");
  }

  assert(index_out < index_to_flow.size());
  index_to_flow.at(index_out) = flow;
  flow_to_index[flow]         = index_out;
}
