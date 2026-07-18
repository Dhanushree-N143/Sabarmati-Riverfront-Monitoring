// ESP32 CAM STREAMER FOR WASTE FLOATER PROJECT

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <time.h>

// ===================== CONFIGURATION =====================
const char* ssid = "Tamil magan";       // Your WiFi Name
const char* password = "28112006";  // Your WiFi Password
const int STREAM_PORT = 8080;      // IMPORTANT: Changed from 80 to 8080 to bypass firewall/port conflicts

// ===================== CAMERA PIN DEFINITIONS =====================
// Standard pinout for ESP32-CAM AI-Thinker model
#define PWDN_GPIO_NUM    -1
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM    21
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27

#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      13
#define Y4_GPIO_NUM      33
#define Y3_GPIO_NUM      32
#define Y2_GPIO_NUM      25
#define VSYNC_GPIO_NUM   22
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    Y9_GPIO_NUM
#define LED_GPIO_NUM     4  // Flash LED pin

// ===================== STREAMING SETUP =====================
WebServer server(STREAM_PORT);

void setup_camera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_sda = SIOD_GPIO_NUM;
    config.pin_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    
    // Choose FRAME SIZE: CIF for low bandwidth, SVGA or XGA for quality.
    config.frame_size = FRAMESIZE_VGA; 
    config.jpeg_quality = 10;
    config.fb_count = 2;

    // Camera Init
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x", err);
        delay(5000);
        ESP.restart();
    }
}

// Function to handle the actual JPEG stream (required by OpenCV)
void handle_jpg_stream() {
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t * _jpg_buf = NULL;
    char * part_buf[64];

    // Set headers for MJPEG stream
    server.sendHeader("Content-Type", "multipart/x-mixed-replace; boundary=123456789000000000000987654321");
    server.send(200, "multipart/x-mixed-replace; boundary=123456789000000000000987654321", "");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Camera capture failed");
            res = ESP_FAIL;
        } else {
            // Convert to JPEG if not already in JPEG format
            if(fb->format != PIXFORMAT_JPEG){
                bool jpeg_converted = frame2jpg(fb, 10, &_jpg_buf, &_jpg_buf_len);
                esp_camera_fb_return(fb);
                fb = NULL;
                if(!jpeg_converted){
                    Serial.println("JPEG conversion failed");
                    res = ESP_FAIL;
                }
            } else {
                _jpg_buf = fb->buf;
                _jpg_buf_len = fb->len;
            }
        }
        
        // Send frame chunk
        if(res == ESP_OK){
            size_t hlen = snprintf((char *)part_buf, 64, "--123456789000000000000987654321\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
            server.sendContent((const char *)part_buf, hlen);    
            server.sendContent((const char *)_jpg_buf, _jpg_buf_len);
            server.sendContent("\r\n", 2);
        }

        if(fb){
            esp_camera_fb_return(fb);
            fb = NULL;
            _jpg_buf = NULL;
        } else if(_jpg_buf){
            free(_jpg_buf);
            _jpg_buf = NULL;
        }
        
        server.handleClient();
        if (res != ESP_OK) break;
    }
}

void setup() {
    Serial.begin(115200); // Higher baud rate for faster logging
    
    // 1. Connect to Wi-Fi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // 2. Initialize Camera
    setup_camera();

    // 3. Start Web Server
    server.on("/stream", handle_jpg_stream); // The streaming endpoint
    server.onNotFound([](){
        server.send(200, "text/html", "<html><body><h1>Waste Floater CAM</h1><img src=\"/stream\"></body></html>");
    });
    server.begin();
    Serial.print("Camera Stream Ready on Port: ");
    Serial.println(STREAM_PORT);
}

void loop() {
    server.handleClient();
}