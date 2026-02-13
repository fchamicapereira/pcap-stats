#include "double_chain.h"

// Requires the array dchain_cell, large enough to fit all the range of
// possible 'index' values + 2 special values.
// Forms a two closed linked lists inside the array.
// First list represents the "free" cells. It is a single linked list.
// Initially the whole array
// (except 2 special cells holding metadata) added to the "free" list.
// Second list represents the "occupied" cells and it is double-linked,
// the order matters.
// It is supposed to store the ordered sequence, and support moving any
// element to the top.
//
// The lists are organized as follows:
//              +----+   +---+   +-------------------+   +-----
//              |    V   |   V   |                   V   |
//  [. + .][    .]  {    .} {    .} {. + .} {. + .} {    .} ....
//   ^   ^                           ^   ^   ^   ^
//   |   |                           |   |   |   |
//   |   +---------------------------+   +---+   +-------------
//   +---------------------------------------------------------
//
// Where {    .} is an "free" list cell, and {. + .} is an "alloc" list cell,
// and dots represent prev/next fields.
// [] - denote the special cells - the ones that are always kept in the
// corresponding lists.
// Empty "alloc" and "free" lists look like this:
//
//   +---+   +---+
//   V   V   V   |
//  [. + .] [    .]
//
// , i.e. cells[0].next == 0 && cells[0].prev == 0 for the "alloc" list, and
// cells[1].next == 1 for the free list.
// For any cell in the "alloc" list, 'prev' and 'next' fields must be different.
// Any cell in the "free" list, in contrast, have 'prev' and 'next' equal;
// After initialization, any cell is allways on one and only one of these lists.

constexpr const int DCHAIN_RESERVED          = 2;
constexpr const time_ns_t EXPIRATION_TIME_NS = 1'000'000'000ULL; // 1 second

enum DCHAIN_ENUM {
  ALLOC_LIST_HEAD = 0,
  FREE_LIST_HEAD  = 1,
  INDEX_SHIFT     = DCHAIN_RESERVED,
};

DoubleChain::DoubleChain(u64 index_range) : cells(index_range + DCHAIN_RESERVED), timestamps(index_range) {
  dchain_cell_t &al_head = cells[ALLOC_LIST_HEAD];
  al_head.prev           = 0;
  al_head.next           = 0;
  u64 i                  = INDEX_SHIFT;

  dchain_cell_t &fl_head = cells[FREE_LIST_HEAD];
  fl_head.next           = i;
  fl_head.prev           = fl_head.next;

  while (i < (index_range + INDEX_SHIFT - 1)) {
    dchain_cell_t &current = cells[i];
    current.next           = i + 1;
    current.prev           = current.next;
    ++i;
  }

  dchain_cell_t &last = cells[i];
  last.next           = FREE_LIST_HEAD;
  last.prev           = last.next;
}

bool DoubleChain::allocate_new_index(time_ns_t time, u64 &index_out) {
  dchain_cell_t &fl_head = cells[FREE_LIST_HEAD];
  dchain_cell_t &al_head = cells[ALLOC_LIST_HEAD];
  const u64 allocated    = fl_head.next;
  if (allocated == FREE_LIST_HEAD) {
    return false;
  }

  dchain_cell_t &allocp = cells[allocated];
  // Extract the link from the "empty" chain.
  fl_head.next = allocp.next;
  fl_head.prev = fl_head.next;

  // Add the link to the "new"-end "alloc" chain.
  allocp.next = ALLOC_LIST_HEAD;
  allocp.prev = al_head.prev;

  dchain_cell_t &alloc_head_prevp = cells[al_head.prev];
  alloc_head_prevp.next           = allocated;
  al_head.prev                    = allocated;

  index_out             = allocated - INDEX_SHIFT;
  timestamps[index_out] = time;
  return true;
}

bool DoubleChain::rejuvenate_index(u64 index, time_ns_t time) {
  const u64 lifted = index + INDEX_SHIFT;

  dchain_cell_t &liftedp = cells[lifted];
  const u64 lifted_next  = liftedp.next;
  const u64 lifted_prev  = liftedp.prev;

  // The index is not allocated.
  if (lifted_next == lifted_prev) {
    if (lifted_next != ALLOC_LIST_HEAD) {
      return false;
    } else {
      // There is only one element allocated - no point in changing
      // anything
      return true;
    }
  }

  dchain_cell_t &lifted_prevp = cells[lifted_prev];
  lifted_prevp.next           = lifted_next;

  dchain_cell_t &lifted_nextp = cells[lifted_next];
  lifted_nextp.prev           = lifted_prev;

  dchain_cell_t &al_head = cells[ALLOC_LIST_HEAD];
  const u64 al_head_prev = al_head.prev;

  // Link it at the very end - right before the special link.
  liftedp.next = ALLOC_LIST_HEAD;
  liftedp.prev = al_head_prev;

  dchain_cell_t &al_head_prevp = cells[al_head_prev];
  al_head_prevp.next           = lifted;
  al_head.prev                 = lifted;

  timestamps[index] = time;

  return true;
}

bool DoubleChain::expire_one_index(time_ns_t time, u64 &index_out) {
  const bool has_ind = get_oldest_index(index_out);
  if (has_ind) {
    if (timestamps[index_out] < time - EXPIRATION_TIME_NS) {
      return free_index(index_out);
    }
  }
  return false;
}

bool DoubleChain::is_index_allocated(u64 index) const {
  const u64 lifted = index + INDEX_SHIFT;

  const dchain_cell_t &liftedp = cells[lifted];
  const u64 lifted_next        = liftedp.next;
  const u64 lifted_prev        = liftedp.prev;

  u64 result;
  if (lifted_next == lifted_prev) {
    if (lifted_next != ALLOC_LIST_HEAD) {
      return false;
    } else {
      return true;
    }
  } else {
    return true;
  }
}

bool DoubleChain::free_index(u64 index) {
  const u64 freed = index + INDEX_SHIFT;

  dchain_cell_t &freedp = cells[freed];
  u64 freed_prev        = freedp.prev;
  u64 freed_next        = freedp.next;

  // The index is already free.
  if (freed_next == freed_prev) {
    if (freed_prev != ALLOC_LIST_HEAD) {
      return false;
    }
  }

  dchain_cell_t &fr_head = cells[FREE_LIST_HEAD];

  // Extract the link from the "alloc" chain.
  dchain_cell_t &freed_prevp = cells[freed_prev];
  freed_prevp.next           = freed_next;

  dchain_cell_t &freed_nextp = cells[freed_next];
  freed_nextp.prev           = freed_prev;

  // Add the link to the "free" chain.
  freedp.next = fr_head.next;
  freedp.prev = freedp.next;

  fr_head.next = freed;
  fr_head.prev = fr_head.next;

  return true;
}

bool DoubleChain::get_oldest_index(u64 &index_out) const {
  const dchain_cell_t &al_head = cells[ALLOC_LIST_HEAD];

  // No allocated indexes.
  if (al_head.next == ALLOC_LIST_HEAD) {
    return false;
  }

  index_out = al_head.next - INDEX_SHIFT;
  return true;
}