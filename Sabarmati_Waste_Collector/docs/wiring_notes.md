WIRING NOTES (short)
- PCA9685 SDA -> GPIO21, SCL -> GPIO22, VCC -> 5V servo rail, GND -> common GND
- TB6612 AIN1->13 AIN2->12 BIN1->27 BIN2->14 PWMA->25 PWMB->26 VM->motor battery, GND->common
- Servos -> PCA9685 channels 3 and 4; servo V+ -> strong 5V regulator; GND common
- Sensors: PH -> GPIO35, Turbidity -> GPIO34 (use voltage divider if sensor outputs up to 5V)
- ESP32 power: USB or regulated 5V. Keep motor battery negative tied to ESP32 GND.
