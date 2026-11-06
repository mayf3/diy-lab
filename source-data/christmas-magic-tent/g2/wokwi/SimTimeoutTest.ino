/*
 * G2-V1 Wokwi 专用：10 分钟空闲超时的"加速验证"草图。
 *
 * 与生产固件 firmware/ChristmasStar.ino 的唯一差别：
 *   controller.update() 收到的是 虚拟时间 millis() * TIME_SCALE（TIME_SCALE=60），
 *   使 600000ms（10 分钟）空闲超时在约 10 秒真实时间内可观察。
 * controller.h 与生产完全相同，一行未改（md5 063985036d6a00dae6f98e0b0715dc54）。
 * 生产固件传原始 millis()，无任何缩放 —— 本文件仅用于 Wokwi 超时证据，不得用于实物。
 */
#include <Adafruit_NeoPixel.h>
#include "controller.h"

constexpr uint8_t BUTTON_PIN = 2;
constexpr uint8_t DATA_PIN = 6;
constexpr uint8_t PIXEL_COUNT = 4;
constexpr uint8_t BRIGHTNESS = 48;
constexpr uint32_t TIME_SCALE = 60;   // 1 真实秒 = 60 虚拟秒；10min 超时 ≈ 10s 真实

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
  controller.begin(millis() * TIME_SCALE, digitalRead(BUTTON_PIN) == LOW);
  Serial.println(F("SIM-TIMEOUT-TEST: idle 10min == 10s real (TIME_SCALE=60)"));
}

void loop() {
  const uint32_t vnow = millis() * TIME_SCALE;   // 虚拟时间只喂给控制器
  controller.update(digitalRead(BUTTON_PIN) == LOW, vnow);
  const StarController::Mode mode = controller.mode();
  if (mode != renderedMode) {
    Serial.print(F("Mode: "));
    Serial.print(static_cast<uint8_t>(mode));
    Serial.print(F(" at virtual_ms="));
    Serial.println(vnow);
    renderedMode = mode;
  }
  const uint32_t now = millis();                 // 真实时间驱动渲染帧
  if (uint32_t(now - lastFrame) < 20) return;
  lastFrame = now;
  const uint16_t hue = static_cast<uint16_t>(((now % 30000UL) * 65535UL) / 30000UL);
  for (uint8_t i = 0; i < PIXEL_COUNT; ++i) {
    uint32_t colour = 0;
    if (mode == StarController::Warm) colour = pixels.Color(255, 120, 30);
    if (mode == StarController::Colour) colour = pixels.ColorHSV(hue, 255, 220);
    pixels.setPixelColor(i, colour);
  }
  pixels.show();
}
