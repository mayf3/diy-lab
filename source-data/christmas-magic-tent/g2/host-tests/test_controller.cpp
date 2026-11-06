#include <cassert>
#include <cstdint>
#include <iostream>
#include "../03_Arduino/ChristmasStar/controller.h"
static void click(StarController &c, uint32_t t) {
  c.update(true,t); c.update(true,t+35);
  c.update(false,t+100); c.update(false,t+135);
}
int main() {
  { StarController c; c.begin(0,false); assert(c.mode()==StarController::Off);
    click(c,10); assert(c.mode()==StarController::Warm);
    click(c,200); assert(c.mode()==StarController::Colour);
    click(c,400); assert(c.mode()==StarController::Off); }
  { StarController c; c.begin(0,false);
    c.update(true,10); c.update(false,15); c.update(true,20); c.update(false,25);
    c.update(false,100); assert(c.mode()==StarController::Off); }
  { StarController c; c.begin(0,false); click(c,10);
    c.update(true,200); c.update(true,235); c.update(true,1434);
    assert(c.mode()==StarController::Warm); c.update(true,1435);
    assert(c.mode()==StarController::Off);
    c.update(false,1500); c.update(false,1535);
    assert(c.mode()==StarController::Off); }
  { StarController c; c.begin(0,true); c.update(true,2000);
    c.update(false,2100); c.update(false,2135);
    assert(c.mode()==StarController::Off); click(c,2200);
    assert(c.mode()==StarController::Warm); }
  { StarController c; c.begin(0,false); click(c,10);
    c.update(false,600144); assert(c.mode()==StarController::Warm);
    c.update(false,600145); assert(c.mode()==StarController::Off); }
  { const uint32_t t=UINT32_MAX-60; StarController c; c.begin(t,false);
    click(c,t+1); assert(c.mode()==StarController::Warm); }
  { StarController c; c.begin(0,false);
    for (uint32_t i=0;i<20;++i) click(c,10+i*200);
    assert(c.mode()==StarController::Colour); }
  std::cout << "PASS: 7 controller scenarios (cycle, debounce, long press, boot hold, timeout, millis rollover, 20 clicks)\n";
}
