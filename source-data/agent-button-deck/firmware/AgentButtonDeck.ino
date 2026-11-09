/*
 * Agent Button Deck | G1 four-button proof of concept.
 *
 * Board: ESP32-S3-DevKitC-1 v1.1 (verify actual board revision first)
 * Transport: board's USB-to-UART bridge, Arduino ESP32 USB CDC On Boot Disabled.
 * Input: NO switches, one side GPIO4..GPIO7, other side GND.
 *
 * Emits exactly one line per debounced PRESS, never credentials or commands:
 * {"v":1,"event":"press","key":"K1"}
 *
 * Uncompiled/unflashed example as of 2026-11-09; physical evidence required.
 */
#include <Arduino.h>

constexpr uint8_t kButtonPins[] = {4, 5, 6, 7};
constexpr size_t kButtonCount = sizeof(kButtonPins) / sizeof(kButtonPins[0]);
constexpr unsigned long kDebounceMs = 35;

bool stableLevel[kButtonCount];
bool lastRawLevel[kButtonCount];
unsigned long lastTransitionMs[kButtonCount];

void emitPress(size_t index) {
  Serial.print(F("{\"v\":1,\"event\":\"press\",\"key\":\"K"));
  Serial.print(index + 1);
  Serial.println(F("\"}"));
}

void setup() {
  Serial.begin(115200);
  for (size_t i = 0; i < kButtonCount; ++i) {
    pinMode(kButtonPins[i], INPUT_PULLUP);
    const bool level = digitalRead(kButtonPins[i]);
    stableLevel[i] = level;
    lastRawLevel[i] = level;
    lastTransitionMs[i] = millis();
  }
}

void loop() {
  const unsigned long now = millis();
  for (size_t i = 0; i < kButtonCount; ++i) {
    const bool raw = digitalRead(kButtonPins[i]);
    if (raw != lastRawLevel[i]) {
      lastRawLevel[i] = raw;
      lastTransitionMs[i] = now;
    }

    if (raw != stableLevel[i] &&
        (unsigned long)(now - lastTransitionMs[i]) >= kDebounceMs) {
      stableLevel[i] = raw;
      if (raw == LOW) {
        emitPress(i);
      }
    }
  }
  delay(2);
}
