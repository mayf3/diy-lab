/*
 * G2-V2 宿主逻辑测试 —— PresenceGreeter（PIR 迎宾）+ StarController 交互优先级。
 * 被测：g2-v2/firmware/greeter.h（新逻辑）；交互优先级用 g2-v1 的
 *       firmware/controller.h 一起演练（两者并存，不互相改动）。
 * 编译运行：c++ -std=c++11 -Wall -o test_g2v2 test_g2v2.cpp && ./test_g2v2
 */
#include <cstdint>
#include <cstdio>
#include "../firmware/greeter.h"
#include "../../g2/firmware/controller.h"

static int g_failures = 0;
#define CHECK(cond) do { if (!(cond)) { printf("  FAIL: %s (line %d)\n", #cond, __LINE__); ++g_failures; } } while (0)
using Mode = StarController::Mode;
using Event = PresenceGreeter::Event;

// 生产默认参数的缩短版（比例保持）：冷却 60ms、Welcome 20ms、Story 30ms。
// 语义与生产一致，只是时间刻度缩短，便于宿主测试。
static PresenceGreeter makeGreeter() { return PresenceGreeter(60, 20, 30); }

int main() {
  // ---- T1 上电默认：PIR 预热高电平不触发 ----
  { PresenceGreeter g = makeGreeter();
    g.begin(0, true, 1);              // 上电时 PIR 已是高电平（HC-SR501 预热）
    g.update(true, 1, 100);
    CHECK(g.event() == Event::None);  // 预热高电平不触发
    g.update(false, 1, 200);          // 下降沿：预热抑制解除
    g.update(true, 1, 300);           // 真正的上升沿
    CHECK(g.event() == Event::Welcome);
    CHECK(g.playing());
    printf("T1  上电默认(预热抑制): PASS\n"); }

  // ---- T2 连续触发防重复 + 冷却结束换事件 ----
  { PresenceGreeter g = makeGreeter();
    g.begin(0, false, 1);
    g.update(true, 1, 10);            // 触发 WELCOME（start=10, end=30）
    g.update(true, 1, 20);            // 播放中
    g.update(false, 1, 25);
    g.update(true, 1, 28);            // 播放中再次触发（仍在 10..30 内）
    CHECK(g.event() == Event::Welcome);   // 忽略：不重启不打断
    g.update(false, 1, 31);           // 播放自然结束
    CHECK(g.event() == Event::None && !g.playing());
    g.update(true, 1, 50);            // 冷却内（10+60=70 未到）：拒绝
    CHECK(g.event() == Event::None);
    g.update(false, 1, 75);
    g.update(true, 1, 80);            // 冷却结束（>=70）：触发 STORY
    CHECK(g.event() == Event::Story);
    printf("T2  连续触发防重复+冷却: PASS\n"); }

  // ---- T3 播放中再次触发：忽略且不打断 ----
  { PresenceGreeter g = makeGreeter();
    g.begin(0, false, 1);
    g.update(true, 1, 10);            // WELCOME, start=10, end=30
    g.update(false, 1, 15);
    g.update(true, 1, 25);            // 播放中的上升沿
    CHECK(g.event() == Event::Welcome);
    CHECK(g.playing());
    g.update(false, 1, 29);
    CHECK(g.playing());               // 未到 30ms 不结束
    g.update(false, 1, 31);
    CHECK(!g.playing() && g.event() == Event::None);
    printf("T3  播放中再触发忽略: PASS\n"); }

  // ---- T4 手动按钮优先级（与 StarController 联演）----
  { StarController c; c.begin(0, false);
    PresenceGreeter g = makeGreeter(); g.begin(0, false, (uint8_t)c.mode());
    // 点亮 Warm
    c.update(true, 10); c.update(true, 45); c.update(false, 110); c.update(false, 145);
    CHECK(c.mode() == Mode::Warm);
    g.update(true, (uint8_t)c.mode(), 150);
    CHECK(g.event() == Event::Welcome);
    // 用户长按关灯：Off -> 演出立即挂起（pressStarted_ 从去抖稳定点 235 起算）
    c.update(true, 200); c.update(true, 235); c.update(true, 235 + 1200);
    CHECK(c.mode() == Mode::Off);
    g.update(true, (uint8_t)c.mode(), 1500);
    CHECK(g.event() == Event::None && !g.playing());
    // Off 期间 PIR 再次触发：仍不播
    c.update(false, 1500); c.update(false, 1535);
    g.update(false, (uint8_t)c.mode(), 1560);
    g.update(true, (uint8_t)c.mode(), 1600);
    CHECK(g.event() == Event::None);
    // 重新点亮后，新上升沿才触发
    c.update(true, 1700); c.update(true, 1735); c.update(false, 1800); c.update(false, 1835);
    CHECK(c.mode() == Mode::Warm);
    g.update(false, (uint8_t)c.mode(), 1850);
    g.update(true, (uint8_t)c.mode(), 1900);
    CHECK(g.event() == Event::Story);   // 事件交替：上次 Welcome，本次 Story
    printf("T4  手动按钮优先级: PASS\n"); }

  // ---- T5 冷却边界（cooldownMs-1 拒绝 / =cooldownMs 通过）----
  { PresenceGreeter g = makeGreeter();
    g.begin(0, false, 1);
    g.update(true, 1, 10);            // start=10, WELCOME 20ms
    g.update(false, 1, 35);
    g.update(true, 1, 10 + 60 - 1);   // 69ms：冷却差 1ms
    CHECK(g.event() == Event::None);
    g.update(false, 1, 71);
    g.update(true, 1, 10 + 60);       // 70ms：恰好冷却期满
    CHECK(g.event() == Event::Story);
    printf("T5  冷却边界(59/60): PASS\n"); }

  // ---- T6 事件交替 WELCOME -> STORY -> WELCOME ----
  { PresenceGreeter g = makeGreeter();
    g.begin(0, false, 1);
    g.update(true, 1, 10);  g.update(false, 1, 40);
    g.update(true, 1, 100); g.update(false, 1, 140);   // 冷却已过（10+60=70）
    g.update(true, 1, 200);                             // 冷却 100+60=160 已过
    CHECK(g.event() == Event::Welcome);
    printf("T6  事件交替: PASS\n"); }

  if (g_failures == 0) {
    printf("\nALL PASS: 6 类行为 / 6 场景（greeter 纯逻辑 + 控制器联演）\n");
    return 0;
  }
  printf("\nFAILED: %d 项断言\n", g_failures);
  return 1;
}
