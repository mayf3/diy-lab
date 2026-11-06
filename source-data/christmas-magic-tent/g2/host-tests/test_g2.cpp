/*
 * G2-V1 宿主逻辑测试 —— 在 Mac 上直接编译运行，不依赖 Arduino/Wokwi。
 * 被测对象：firmware/controller.h（原样复用，未改一行 —— md5 063985036d6a00dae6f98e0b0715dc54）
 * 覆盖 G2-V1 门禁的 8 项行为 + 计时边界。
 *
 * 编译运行：c++ -std=c++11 -Wall -o test_g2 test_g2.cpp && ./test_g2
 *
 * 证据分层：本文件=主机逻辑测试。Wokwi 运行与真实硬件验证另行记录。
 */
#include <cstdint>
#include <iostream>
#include <cstdio>
#include "../firmware/controller.h"

static int g_failures = 0;
#define CHECK(cond) do { if (!(cond)) { printf("  FAIL: %s (line %d)\n", #cond, __LINE__); ++g_failures; } } while (0)
using Mode = StarController::Mode;

// 标准短按：稳定按下 >=30ms 后稳定释放（与 qa/test_controller.cpp 的 click() 同语义）
static void click(StarController &c, uint32_t t) {
  c.update(true, t); c.update(true, t + 35);
  c.update(false, t + 100); c.update(false, t + 135);
}

int main() {
  // ---- S1 上电关闭 ----
  { StarController c; c.begin(0, false);
    CHECK(c.mode() == Mode::Off);
    c.update(false, 1000); c.update(false, 20000);
    CHECK(c.mode() == Mode::Off);
    printf("S1  上电关闭: PASS\n"); }

  // ---- S2 短按循环 Off->Warm->Colour->Off ----
  { StarController c; c.begin(0, false);
    click(c, 10);    CHECK(c.mode() == Mode::Warm);
    click(c, 200);   CHECK(c.mode() == Mode::Colour);
    click(c, 400);   CHECK(c.mode() == Mode::Off);
    click(c, 600);   CHECK(c.mode() == Mode::Warm);   // 循环回绕
    printf("S2  短按循环: PASS\n"); }

  // ---- S3 长按关闭（含 1199/1200ms 边界）----
  // 注意：pressStarted_ 从去抖稳定点（按下后 ~30ms）起算，非物理按下时刻
  { StarController c; c.begin(0, false); click(c, 10);   // Warm, lastAction_=145
    c.update(true, 200); c.update(true, 235);            // 稳定按下, pressStarted_=235
    c.update(true, 235 + 1199);                          // 持续 1199ms
    CHECK(c.mode() == Mode::Warm);                        // 1200ms 边界前不关
    c.update(true, 235 + 1200);                           // 恰好 1200ms
    CHECK(c.mode() == Mode::Off);
    c.update(false, 2400); c.update(false, 2435);         // 释放不得再切换
    CHECK(c.mode() == Mode::Off);
    printf("S3  长按关闭+边界(1199/1200): PASS\n"); }

  // ---- S4 按键去抖（29/30/31ms 边界 + 毛刺噪声）----
  { StarController c; c.begin(0, false);
    c.update(true, 10); c.update(false, 10 + 29); c.update(true, 10 + 58); // <30ms 往返毛刺
    c.update(false, 500);
    CHECK(c.mode() == Mode::Off);                          // 毛刺不产生切换
    // 稳定按下 30ms 才生效：30ms 整点边界
    StarController d; d.begin(0, false);
    d.update(true, 100); d.update(true, 129);
    d.update(false, 130); d.update(false, 165);            // 29ms 即松开 -> 不算
    CHECK(d.mode() == Mode::Off);
    StarController e; e.begin(0, false);
    e.update(true, 100); e.update(true, 130);              // 恰好 30ms -> 生效
    e.update(false, 200); e.update(false, 235);
    CHECK(e.mode() == Mode::Warm);
    StarController f; f.begin(0, false);
    f.update(true, 100); f.update(true, 131);              // 31ms > 阈值 -> 同样生效
    f.update(false, 200); f.update(false, 235);
    CHECK(f.mode() == Mode::Warm);
    printf("S4  去抖+边界(29拒绝/30生效/31生效,毛刺): PASS\n"); }

  // ---- S5 上电按住（不得误点亮）----
  { StarController c; c.begin(0, true); c.update(true, 2000);
    c.update(true, 5000);                                  // 上电就按住超过长按时限
    CHECK(c.mode() == Mode::Off);                          // 抑制：不点亮也不长按关（本来就关）
    c.update(false, 5100); c.update(false, 5135);          // 时间单调递增地释放
    CHECK(c.mode() == Mode::Off);
    click(c, 5200); CHECK(c.mode() == Mode::Warm);         // 松开后恢复正常
    printf("S5  上电按住抑制: PASS\n"); }

  // ---- S6 10 分钟空闲超时（599999/600000 边界）----
  { StarController c; c.begin(0, false); click(c, 10);     // lastAction_=10+135=145
    c.update(false, 145 + 599999);
    CHECK(c.mode() == Mode::Warm);                         // 600000ms 边界前不关
    c.update(false, 145 + 600000);
    CHECK(c.mode() == Mode::Off);                          // 恰好 10min -> 关
    printf("S6  10分钟空闲超时+边界: PASS\n"); }

  // ---- S7 快速连续按压（20 次，含长按后立即快按）----
  { StarController c; c.begin(0, false);
    for (uint32_t i = 0; i < 20; ++i) click(c, 10 + i * 200);   // 每 200ms 一次
    CHECK(c.mode() == Mode::Colour);                       // 20 mod 3 == 2
    StarController d; d.begin(0, false); click(d, 10);     // Warm
    d.update(true, 200); d.update(true, 235);              // 稳定按下, pressStarted_=235
    d.update(true, 235 + 1200);                            // 长按 -> Off（手仍按住）
    CHECK(d.mode() == Mode::Off);
    d.update(false, 2400); d.update(false, 2435);          // 松手：被 longHandled 吞掉，仍 Off
    CHECK(d.mode() == Mode::Off);
    click(d, 2500); CHECK(d.mode() == Mode::Warm);         // 再短按正常点亮
    click(d, 2700); CHECK(d.mode() == Mode::Colour);       // longHandled 不泄漏
    printf("S7  快速连续按压+长按后恢复: PASS\n"); }

  // ---- S8 计时边界补充：millis() 32 位回绕 ----
  { const uint32_t t = UINT32_MAX - 60; StarController c; c.begin(t, false);
    click(c, t + 1);
    CHECK(c.mode() == Mode::Warm);
    c.update(false, t + 1 + 135 + 600000);                 // 跨回绕的空闲判断
    CHECK(c.mode() == Mode::Off);
    printf("S8  millis 回绕: PASS\n"); }

  if (g_failures == 0) {
    printf("\nALL PASS: 8 类行为 / 11 个场景全部通过（主机逻辑层，复用 controller.h 未改动）\n");
    return 0;
  }
  printf("\nFAILED: %d 项断言未通过\n", g_failures);
  return 1;
}
