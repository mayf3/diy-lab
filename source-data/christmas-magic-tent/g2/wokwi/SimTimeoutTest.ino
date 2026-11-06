/*
 * G2-V1 Wokwi 专用：自动熄灯演示版草图（10 秒空闲熄灯）。
 *
 * 与生产固件 firmware/ChristmasStar.ino 的唯一差异：
 *   #include "controller_idle10s.h"（IdleMs 600000 -> 10000，仅缩短空闲超时；
 *   去抖 30ms 与长按 1200ms 与生产完全一致）。controller.h 一行未改。
 * 10 分钟阈值的行为验证由主机逻辑测试 S6（599999/600000 边界）覆盖；
 * 本文件仅用于在 Wokwi 中可视化"点亮后静置自动熄灯"（约 10 秒），不得用于实物。
 * 交互验证（短按/长按/去抖）请使用生产固件 ChristmasStar.ino。
 */
#include <Adafruit_NeoPixel.h>
#include "controller_idle10s.h"

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
  Serial.println(F("IDLE10S DEMO (test only): short click cycles warm/colour/off; hold 1.2s to turn off; auto-off after 10s idle."));
}

void loop() {
  const uint32_t now = millis();   // 原始 millis()——无任何时间缩放
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
