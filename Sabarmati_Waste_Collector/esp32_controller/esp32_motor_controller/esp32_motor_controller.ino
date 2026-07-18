#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ================= CONFIGURATION =================
const char* ssid = "Tamil magan";      // Your WiFi Name
const char* password = "28112006";  // Your WiFi Password
const char* ESP32_IP = "192.168.139.88"; // Assumed Motor Controller IP

// Servo Pulse Range (Constants for degToPulse function)
const int SERVO_MIN_PULSE = 110;  // Minimum pulse length (0 degrees)
const int SERVO_MAX_PULSE = 490;  // Maximum pulse length (180 degrees)
// =================================================

WebServer server(80);
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// Servo Channels
const int SERVO_CH_1 = 3; // Left Servo Channel
const int SERVO_CH_2 = 4; // Right Servo Channel

// Motor Pins (Adjust based on your H-Bridge/Motor Shield)
const int AIN1 = 13; const int AIN2 = 12;
const int BIN1 = 27; const int BIN2 = 14;
const int PWMA = 25; const int PWMB = 26;

// Helper function to map degrees to pulse width
int degToPulse(int deg) {
    // Uses the constants defined globally
    return map(deg, 0, 180, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
}

// Helper to set pulse widths directly for maximum synchronization
void setServoPulse(int p1, int p2) {
    pwm.setPWM(SERVO_CH_1, 0, p1);
    pwm.setPWM(SERVO_CH_2, 0, p2);
}

void collectSequence() {
    Serial.println("Starting FINAL Collection Sequence (3x UP, 2x DOWN) - Ends on DOWN.");
    
    // Define the pulse widths for direct control 
    const int PULSE_DOWN_GRAB_L = 405; 
    const int PULSE_DOWN_GRAB_R = 185;
    const int PULSE_UP_DUMP_L = 185; 
    const int PULSE_UP_DUMP_R = 405; 
    const int PULSE_NEUTRAL = 300; // Not used for the final move
    const int MOVE_DELAY = 500; 
    
    // ===========================================
    // CRITICAL PRE-PHASE: Move to the starting DOWN position
    // We keep this to guarantee the first 3 UP motions are full sweeps.
    // ===========================================
    Serial.println("Pre-Phase: Moving arm to initial DOWN/GRAB position.");
    setServoPulse(PULSE_DOWN_GRAB_L, PULSE_DOWN_GRAB_R); 
    delay(MOVE_DELAY); // Wait for the arm to settle

    // ===================================
    // PHASE 1: THREE CONSECUTIVE UP MOTIONS
    // ===================================
    Serial.println("Phase 1: 3x UP Motions");
    for (int i = 0; i < 3; i++) {
        setServoPulse(PULSE_UP_DUMP_L, PULSE_UP_DUMP_R); 
        delay(MOVE_DELAY);
    }
    
    // ===================================
    // PHASE 2: TWO CONSECUTIVE DOWN MOTIONS
    // Arm will stop at the end of this phase (DOWN position)
    // ===================================
    Serial.println("Phase 2: 2x DOWN Motions (Final Position)");
    for (int i = 0; i < 2; i++) {
        setServoPulse(PULSE_DOWN_GRAB_L, PULSE_DOWN_GRAB_R); 
        delay(MOVE_DELAY);
    }

    // ===================================
    // PHASE 3: RETURN TO NEUTRAL (REMOVED)
    // ===================================
    Serial.println("Sequence Complete. Arm remains in DOWN position.");
    // The arm stays in the position set by the last command in Phase 2.
    delay(500); 
}
void stopMotors() {
    digitalWrite(AIN1, LOW); digitalWrite(AIN2, LOW);
    digitalWrite(BIN1, LOW); digitalWrite(BIN2, LOW);
    digitalWrite(PWMA, LOW); digitalWrite(PWMB, LOW);
}

// Basic Motor Movements
void moveBoat(char cmd) {
    if (cmd == 'F') {
        digitalWrite(AIN1, LOW); digitalWrite(AIN2, HIGH);
        digitalWrite(BIN1, LOW); digitalWrite(BIN2, HIGH);
        digitalWrite(PWMA, HIGH); digitalWrite(PWMB, HIGH);
    } else if (cmd == 'L') {
        digitalWrite(AIN1, LOW); digitalWrite(AIN2, LOW);
        digitalWrite(BIN1, LOW); digitalWrite(BIN2, HIGH);
        digitalWrite(PWMA, LOW); digitalWrite(PWMB, HIGH);
    } else if (cmd == 'R') {
        digitalWrite(AIN1, LOW); digitalWrite(AIN2, HIGH);
        digitalWrite(BIN1, LOW); digitalWrite(BIN2, LOW);
        digitalWrite(PWMA, HIGH); digitalWrite(PWMB, LOW);
    } else {
        stopMotors();
    }
}

// THE BRAIN: Decides what to do based on command
void handleCmd() {
    if (!server.hasArg("c")) { server.send(400, "text/plain", "missing c"); return; }
    
    char c = toupper(server.arg("c")[0]);
    
    server.send(200, "text/plain", "OK");

    if (c == 'F' || c == 'L' || c == 'R') {
        
        // 1. START MOVEMENT 
        moveBoat(c); 
        
        // 2. Commit to Driving (Python waits 7s, so 3s drive is fine)
        Serial.print("Action: Committing to ");
        Serial.print(c);
        Serial.println(" for 3 seconds.");
        delay(3000); 
        
        // 3. Stop the Boat
        stopMotors();
        delay(500); 
        
        // 4. Activate Servo Arm
        collectSequence(); 
        
    } else {
        // Command is 'S' (Stop)
        stopMotors();
    }
}

void setup() {
    // Disable brownout detection for stability
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
    
    Serial.begin(9600);
    
    // Setup Motor Pins
    pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT);
    pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT);
    pinMode(PWMA, OUTPUT); pinMode(PWMB, OUTPUT);
    stopMotors();

    // Setup Servos
    Wire.begin(); 
    pwm.begin(); 
    pwm.setPWMFreq(50);
    // Start at the Neutral pulse (90 degrees)
    setServoPulse(degToPulse(90), degToPulse(90)); 

    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to: ");
    Serial.println(ssid);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected!");
    Serial.print("IP Address (Motor): ");
    Serial.println(WiFi.localIP());

    // Start Server
    server.on("/cmd", handleCmd);
    server.begin();
}

void loop() {
    server.handleClient();
}