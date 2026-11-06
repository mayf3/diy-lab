#ifndef CHRISTMAS_STAR_GREETER_H
#define CHRISTMAS_STAR_GREETER_H
#include <stdint.h>

// G2-V2: PIR-triggered welcome greeter — pure logic, Arduino-independent,
// exercised by host tests (g2-v2/host-tests/test_g2v2.cpp).
//
// 与 G2-V1 的 StarController 并存使用（不改动它）：sketch 每帧把
// StarController::mode() 作为 lightMode 传入（0 = Off）。
//
// 设计语义（G2-V2 验收口径）：
//   * PIR 上升沿 = 有人进入；播放 Welcome / Story 两个事件交替（声音由
//     sketch 层映射到 PLAY_WELCOME / PLAY_STORY，本类只产生事件）。
//   * 冷却：距上次触发 < CooldownMs 时不重播（防重复欢迎）。
//   * 播放中再次触发：忽略（不重启、不排队）。
//   * 手动按钮优先：lightMode == Off（用户关灯）时演出立即挂起，且 Off 期间
//     PIR 不触发；灯重新点亮后需新的上升沿才触发。
//   * 上电默认：Idle。若 begin 时 PIR 已是高电平（HC-SR501 预热输出），
//     抑制到第一个下降沿为止，之后才允许上升沿触发。
class PresenceGreeter {
 public:
  enum Event : uint8_t { None, Welcome, Story };

  // 默认参数=生产建议值；测试可注入更短时间。
  explicit PresenceGreeter(uint32_t cooldownMs = 15000,
                           uint32_t welcomeMs = 3000,
                           uint32_t storyMs = 5000)
    : cooldownMs_(cooldownMs), welcomeMs_(welcomeMs), storyMs_(storyMs) {}

  void begin(uint32_t now, bool motion, uint8_t lightMode) {
    (void)lightMode;
    raw_ = motion;
    suppress_ = motion;   // PIR 上电预热高电平：等第一个下降沿解除
    playing_ = false;
    event_ = None;
    nextEvent_ = Welcome;
    everPlayed_ = false;
    start_ = lastStart_ = now;
    duration_ = 0;
    prevMotion_ = motion;
  }

  // lightMode: 0 = Off（演出挂起），非 0 = Warm/Colour（演出允许）。
  void update(bool motion, uint8_t lightMode, uint32_t now) {
    if (lightMode == 0) {          // 手动按钮优先：Off 挂起演出
      playing_ = false;
      event_ = None;
      raw_ = motion;
      prevMotion_ = motion;        // 恢复后不产生假上升沿
      if (!motion) suppress_ = false;
      return;
    }
    if (motion != raw_) {
      raw_ = motion;
      if (!motion && suppress_) suppress_ = false;   // 预热抑制解除
    }
    if (playing_ && uint32_t(now - start_) >= duration_) {
      playing_ = false;
      event_ = None;
    }
    const bool rising = motion && !prevMotion_;
    prevMotion_ = motion;
    if (!playing_ && !suppress_ && rising &&
        (!everPlayed_ || uint32_t(now - lastStart_) >= cooldownMs_)) {
      playing_ = true;
      event_ = nextEvent_;
      duration_ = (event_ == Welcome) ? welcomeMs_ : storyMs_;
      start_ = now;
      lastStart_ = now;
      everPlayed_ = true;
      nextEvent_ = (nextEvent_ == Welcome) ? Story : Welcome;   // 交替
    }
  }

  Event event() const { return event_; }   // None = 无声音事件
  bool playing() const { return playing_; }

 private:
  uint32_t cooldownMs_, welcomeMs_, storyMs_;
  bool raw_ = false, prevMotion_ = false;
  bool suppress_ = false;      // 上电预热抑制
  bool playing_ = false;
  bool everPlayed_ = false;
  Event event_ = None, nextEvent_ = Welcome;
  uint32_t start_ = 0, lastStart_ = 0, duration_ = 0;
};
#endif
