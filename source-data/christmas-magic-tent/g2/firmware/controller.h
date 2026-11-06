#ifndef CHRISTMAS_STAR_CONTROLLER_H
#define CHRISTMAS_STAR_CONTROLLER_H
#include <stdint.h>

// Independent of Arduino: the same interaction logic is exercised by the host tests.
class StarController {
 public:
  enum Mode : uint8_t { Off, Warm, Colour };
  static const uint32_t DebounceMs = 30;
  static const uint32_t LongPressMs = 1200;
  static const uint32_t IdleMs = 600000;

  void begin(uint32_t now, bool pressed) {
    mode_ = Off;
    raw_ = stable_ = pressed;
    suppressUntilRelease_ = pressed;  // Holding the button at boot must not turn the light on.
    longHandled_ = false;
    rawChanged_ = pressStarted_ = lastAction_ = now;
  }

  void update(bool pressed, uint32_t now) {
    if (pressed != raw_) { raw_ = pressed; rawChanged_ = now; }
    if (raw_ != stable_ && uint32_t(now - rawChanged_) >= DebounceMs) {
      stable_ = raw_;
      if (stable_) {
        pressStarted_ = now;
        longHandled_ = false;
      } else {
        if (suppressUntilRelease_) {
          suppressUntilRelease_ = false;
        } else if (!longHandled_) {
          mode_ = static_cast<Mode>((static_cast<uint8_t>(mode_) + 1) % 3);
        }
        lastAction_ = now;
      }
    }
    if (stable_ && !suppressUntilRelease_ && !longHandled_ &&
        uint32_t(now - pressStarted_) >= LongPressMs) {
      mode_ = Off;
      longHandled_ = true;            // The subsequent release is not a short click.
      lastAction_ = now;
    }
    if (mode_ != Off && uint32_t(now - lastAction_) >= IdleMs) mode_ = Off;
  }
  Mode mode() const { return mode_; }

 private:
  Mode mode_ = Off;
  bool raw_ = false, stable_ = false;
  bool suppressUntilRelease_ = false, longHandled_ = false;
  uint32_t rawChanged_ = 0, pressStarted_ = 0, lastAction_ = 0;
};
#endif
