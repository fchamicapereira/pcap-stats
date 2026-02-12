#pragma once

#include "types.h"

#include <map>
#include <cmath>

class CDF {
private:
  // The choice of a map instead of a unordered_map here is intentional, as we need to iterate over the values in sorted order to compute the CDF.
  std::map<u64, u64> values;
  u64 total;

public:
  CDF() : total(0) {}

  void add(u64 value) {
    values[value]++;
    total++;
  }

  void add(u64 value, u64 count) {
    values[value] += count;
    total += count;
  }

  std::map<u64, double> get_cdf() const {
    std::map<u64, double> cdf;
    u64 accounted = 0;

    double next_p = 0;
    double step   = 0.05;

    for (const auto &[value, count] : values) {
      accounted += count;

      if (accounted == total) {
        cdf[value] = 1;
        break;
      }

      double p = static_cast<double>(accounted) / total;

      if (p >= next_p) {
        cdf[value] = p;

        while (p >= next_p) {
          next_p += step;
        }
      }
    }

    return cdf;
  }

  double get_avg() const {
    double avg = 0;
    for (const auto &[value, count] : values) {
      avg += value * count;
    }
    return avg / total;
  }

  double get_stdev() const {
    double avg   = get_avg();
    double stdev = 0;
    for (const auto &[value, count] : values) {
      stdev += (value - avg) * (value - avg) * count;
    }
    return sqrt(stdev / total);
  }
};