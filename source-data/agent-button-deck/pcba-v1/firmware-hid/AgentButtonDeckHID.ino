/*
 * AgentButtonDeckHID.ino — Button Deck R1 固件草稿（USB HID 键盘模式）
 *
 * 目标行为（与 5654c5d 串口版事件语义一致，输出改为真实键盘按键）：
 *   - K1–K4 接 GPIO4–7，常开、按下接地；INPUT_PULLUP 用 MCU 内部上拉
 *   - 35 ms 去抖；按下沿发送 F13/F14/F15/F16；松开不发事件；开机按住不补发
 *   - HID 通过 ESP32-S3 原生 USB OTG 口（USB-C/Micro 以实物为准）连接电脑
 *   - Micro-USB（USB-to-UART）口保留为烧录与维护口
 *
 * 状态：草稿，未编译、未烧录、未实测。首次编译时锁定并记录：
 *   - arduino-esp32 Core 版本与 FQBN（板型 esp32s3，USB CDC On Boot = Disabled）
 *   - USBHIDKeyboard 所需的 USB 模式菜单项与编译日志
 * 参考基线：origin/feat/agent-button-deck-doavr@5654c5d 的 AgentButtonDeck.ino
 */

#include "USB.h"
#include "USBHIDKeyboard.h"

// K1–K4 → F13–F16：macOS 上极少冲突的功能键，适合由用户自行绑定动作
static const uint8_t kKeyCodes[4] = { KEY_F13, KEY_F14, KEY_F15, KEY_F16 };
static const int kPins[4] = { 4, 5, 6, 7 };

static const unsigned long kDebounceMs = 35;  // 与 5654c5d 相同的去抖时长
static const unsigned long kPollDelayMs = 2;  // 与 5654c5d 相同的轮询间隔

USBHIDKeyboard Keyboard;

struct ButtonState {
  int lastRaw = HIGH;      // 上一次采样的原始电平
  int stable = HIGH;       // 去抖后的稳定电平
  unsigned long lastEdgeMs = 0;
};

static ButtonState states[4];

void setup() {
  // GPIO4–7 内部上拉；开机读到的电平同时作为原始与稳定初态（按住开机不补发）
  for (int i = 0; i < 4; ++i) {
    pinMode(kPins[i], INPUT_PULLUP);
    states[i].lastRaw = states[i].stable = digitalRead(kPins[i]);
    states[i].lastEdgeMs = millis();
  }
  Keyboard.begin();
  // 等待主机完成 USB 枚举（首次插拔以实测为准；此延时不是已测得的最短枚举时间）
  delay(1500);
}

void loop() {
  const unsigned long now = millis();
  for (int i = 0; i < 4; ++i) {
    const int raw = digitalRead(kPins[i]);
    if (raw != states[i].lastRaw) {
      states[i].lastRaw = raw;
      states[i].lastEdgeMs = now;
    } else if (raw != states[i].stable &&
               now - states[i].lastEdgeMs >= kDebounceMs) {
      states[i].stable = raw;
      if (states[i].stable == LOW) {
        // 按下沿：发送一次 F13–F16；松开与长按均不重复发送
        Keyboard.press(kKeyCodes[i]);
        delay(8);                       // HID 报告间隔，保证按下事件送达
        Keyboard.release(kKeyCodes[i]);
      }
    }
  }
  delay(kPollDelayMs);
}
