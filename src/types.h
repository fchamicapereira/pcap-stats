#pragma once

#include <cstdint>
#include <iomanip>
#include <iostream>

using u64 = __UINT64_TYPE__;
using u32 = __UINT32_TYPE__;
using u16 = __UINT16_TYPE__;
using u8  = __UINT8_TYPE__;

using i64 = __INT64_TYPE__;
using i32 = __INT32_TYPE__;
using i16 = __INT16_TYPE__;
using i8  = __INT8_TYPE__;

using bits_t      = u32;
using bytes_t     = u32;
using code_path_t = u16;
using addr_t      = u64;

using time_s_t  = i64;
using time_ms_t = i64;
using time_us_t = i64;
using time_ns_t = i64;
using time_ps_t = i64;

using pps_t = u64;
using bps_t = u64;
using Bps_t = u64;

using fpm_t = u64;
using fps_t = u64;

constexpr const u64 THOUSAND = 1000LLU;
constexpr const u64 MILLION  = THOUSAND * THOUSAND;
constexpr const u64 BILLION  = MILLION * THOUSAND;
constexpr const u64 TRILLION = BILLION * THOUSAND;

#define align_to_byte(B) ((B) % 8 == 0 ? (B) : (B) + 8 - (B) % 8)
#define bswap16(x) __builtin_bswap16(x)
#define bswap32(x) __builtin_bswap32(x)

inline std::string byte_array_to_string(const u8 *array, size_t size) {
  std::stringstream ss;

  ss << "0x";
  for (size_t i = 0; i < size; i++) {
    ss << std::hex << std::setw(2) << std::setfill('0') << (int)array[i];
  }

  return ss.str();
}

pps_t bps2pps(bps_t bps, bytes_t pkt_size);
bps_t pps2bps(pps_t pps, bytes_t pkt_size);
std::string int2hr(i64 value);
std::string scientific(double value);
std::string tput2str(u64 thpt, std::string units, bool human_readable = false);
std::string percent2str(double value, int precision);
std::string percent2str(double numerator, double denominator, int precision);
bits_t bits_from_pow2_capacity(size_t capacity);
