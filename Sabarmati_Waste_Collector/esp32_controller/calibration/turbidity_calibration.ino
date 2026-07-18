// Simple turbidity raw ADC reader to help with calibration
void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  delay(2000);
  Serial.println("Turbidity calibration tool - read ADC voltage");
}

void loop() {
  int raw = analogRead(34); // TURB_PIN
  float v = raw / 4095.0 * 3.3;
  Serial.printf("raw:%d V:%.3f\n", raw, v);
  delay(1000);
}
