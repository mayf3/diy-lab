/* ChristmasStar — tutorial baseline: confirmed UNO R3 / ATmega328P / 5V only.
   D2 -> momentary NO button -> GND (INPUT_PULLUP)
   D6 -> 330 ohm series resistor -> 5V WS2812B RGB DIN
   5V/GND -> FOUR pixels maximum; 1000uF >=10V across their power input.
   Single power entry through UNO USB. No external supply on 5V/VIN.
   This sketch is not a hardware/electrical safety certification.
*/
#if !defined(ARDUINO_AVR_UNO)
#error "Select confirmed Arduino UNO R3 / ATmega328P; do not reuse this wiring for other boards."
#endif
#include <Adafruit_NeoPixel.h>
#include "controller.h"

constexpr uint8_t BUTTON_PIN = 2;
constexpr uint8_t DATA_PIN = 6;
constexpr uint8_t PIXEL_COUNT = 4;
constexpr uint8_t BRIGHTNESS = 48;  // 0..255, set once. Not a substitute for power sizing.
static_assert(PIXEL_COUNT >= 1 && PIXEL_COUNT <= 4, "Recalculate supply before adding pixels.");
Adafruit_NeoPixel pixels(PIXEL_COUNT, DATA_PIN, NEO_GRB + NEO_KHZ800);
StarController controller;
uint32_t lastFrame = 0;
StarController::Mode renderedMode = StarController::Off;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(9600);
  pixels.begin();
  pixels.setBrightness(BRIGHTNESS);
  pixels.clear();
  pixels.show();
  controller.begin(millis(), digitalRead(BUTTON_PIN) == LOW);
  Serial.println(F("OFF: short click cycles warm/colour/off; hold 1.2s to turn off."));
}

void loop() {
  const uint32_t now = millis();
  controller.update(digitalRead(BUTTON_PIN) == LOW, now);
  const StarController::Mode mode = controller.mode();
  if (mode == renderedMode && uint32_t(now - lastFrame) < 20) return;
  if (mode != renderedMode) {
    Serial.print(F("Mode: "));
    Serial.println(static_cast<uint8_t>(mode));
  }
  lastFrame = now;
  renderedMode = mode;
  const uint16_t hue = static_cast<uint16_t>(((now % 30000UL) * 65535UL) / 30000UL);
  for (uint8_t i = 0; i < PIXEL_COUNT; ++i) {
    uint32_t colour = 0;
    if (mode == StarController::Warm) colour = pixels.Color(255, 120, 30);
    if (mode == StarController::Colour) colour = pixels.ColorHSV(hue, 255, 220);
    pixels.setPixelColor(i, colour);
  }
  pixels.show();
}
