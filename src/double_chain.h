#pragma once

#include "types.h"

#include <vector>

struct dchain_cell_t {
  u64 prev;
  u64 next;
};

class DoubleChain {
  std::vector<dchain_cell_t> cells;
  std::vector<time_ns_t> timestamps;

public:
  DoubleChain(u64 index_range);

  bool allocate_new_index(time_ns_t time, u64 &index_out);
  bool rejuvenate_index(u64 index, time_ns_t time);
  bool expire_one_index(time_ns_t time, u64 &index_out);
  bool is_index_allocated(u64 index) const;
  bool free_index(u64 index);

private:
  bool get_oldest_index(u64 &index_out) const;
};