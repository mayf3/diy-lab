// Maker Lab: lesson 2. A two-terminal normally-open momentary switch
// connects D2 to GND. No 5V wire and no external resistor on the switch.
// USB is the ONLY power input; disconnect USB before changing wires.
#if !defined(ARDUINO_AVR_UNO)
#error "Choose Arduino Uno (UNO R3 / ATmega328P)."
#endif
constexpr unsigned char BUTTON_PIN = 2;
bool previousRaw = false;
bool stablePressed = false;
unsigned long changedAt = 0;
void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
}
void loop() {
  const unsigned long now = millis();
  const bool pressed = digitalRead(BUTTON_PIN) == LOW;
  if (pressed != previousRaw) {
    previousRaw = pressed; changedAt = now;
  }
  if ((unsigned long)(now - changedAt) >= 30) stablePressed = pressed;
  digitalWrite(LED_BUILTIN, stablePressed ? HIGH : LOW);
  delay(2);
}
