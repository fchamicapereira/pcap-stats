#pragma once

#include "types.h"

struct simulator_clock_t {
  const time_ns_t epoch_duration;

  bool on;
  time_ns_t alarm;

  simulator_clock_t(time_ns_t _epoch_duration) : epoch_duration(_epoch_duration), on(false), alarm(0) {}

  bool tick(time_ns_t now) {
    bool sound_alarm = false;

    if (!on) {
      on    = true;
      alarm = now + epoch_duration;
    } else if (now >= alarm) {
      alarm       = now + epoch_duration;
      sound_alarm = true;
    }

    return sound_alarm;
  }
};
