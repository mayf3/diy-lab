// Maker Lab: lesson 1. UNO R3, built-in L LED only.
// USB is the only power input; disconnect all external modules.
#if !defined(ARDUINO_AVR_UNO)
#error "Choose Arduino Uno (UNO R3 / ATmega328P)."
#endif
void setup() { pinMode(LED_BUILTIN, OUTPUT); }
void loop() {
  digitalWrite(LED_BUILTIN, HIGH); delay(1000);
  digitalWrite(LED_BUILTIN, LOW); delay(1000);
}
