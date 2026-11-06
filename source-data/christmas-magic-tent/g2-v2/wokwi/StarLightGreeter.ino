/*
 * G2-V2 Wokwi 集成演示：StarController（G2-V1 原版）+ PresenceGreeter（G2-V2）。
 * D2 = 模式按钮（键盘 Q）；D3 = PIR 信号（滑动开关模拟，HIGH=有人活动）；
 * D6 = 4x WS2812。声音 = 串口事件 [PLAY_WELCOME]/[PLAY_STORY]/[AUDIO_DONE]，
 * 仅事件模拟 —— 不宣称 DFPlayer 已验证，无音频器件。
 * 生产参数：冷却 15s、Welcome 3s、Story 5s（Wokwi 里时间真实流逝）。
 */
#include <Adafruit_NeoPixel.h>
/* Wokwi 使用方法：把 firmware/controller.h 与 firmware/greeter.h 复制到
   Wokwi 项目根目录（与 sketch 同级），这两个 include 才能解析。
   仓库内路径仅供本地阅读，Wokwi 编辑器不识别 ../ 相对路径。 */
#include "controller.h"
#include "greeter.h"

constexpr uint8_t BUTTON_PIN = 2;
constexpr uint8_t PIR_PIN = 3;
constexpr uint8_t DATA_PIN = 6;
constexpr uint8_t PIXEL_COUNT = 4;
constexpr uint8_t BRIGHTNESS = 48;

Adafruit_NeoPixel pixels(PIXEL_COUNT, DATA_PIN, NEO_GRB + NEO_KHZ800);
StarController controller;
PresenceGreeter greeter;          // 默认：冷却 15000 / Welcome 3000 / Story 5000
uint32_t lastFrame = 0;
StarController::Mode renderedMode = StarController::Off;
PresenceGreeter::Event renderedEvent = PresenceGreeter::None;
bool pirRaw = false;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(PIR_PIN, INPUT);
  Serial.begin(9600);
  pixels.begin();
  pixels.setBrightness(BRIGHTNESS);
  pixels.clear();
  pixels.show();
  controller.begin(millis(), digitalRead(BUTTON_PIN) == LOW);
  greeter.begin(millis(), digitalRead(PIR_PIN) == HIGH, (uint8_t)controller.mode());
  Serial.println(F("G2-V2: Q=mode short/long; switch=PIR. Sound is EVENT SIM only."));
}

void loop() {
  const uint32_t now = millis();
  controller.update(digitalRead(BUTTON_PIN) == LOW, now);
  const bool motion = digitalRead(PIR_PIN) == HIGH;
  if (motion != pirRaw) {
    Serial.println(motion ? F("[PIR] motion detected") : F("[PIR] clear"));
    pirRaw = motion;
  }
  greeter.update(motion, (uint8_t)controller.mode(), now);
  const PresenceGreeter::Event ev = greeter.event();
  if (ev != renderedEvent) {
    if (ev == PresenceGreeter::Welcome) Serial.println(F("[PLAY_WELCOME]"));
    if (ev == PresenceGreeter::Story)   Serial.println(F("[PLAY_STORY]"));
    if (ev == PresenceGreeter::None && renderedEvent != PresenceGreeter::None)
      Serial.println(F("[AUDIO_DONE]"));
    renderedEvent = ev;
  }
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
