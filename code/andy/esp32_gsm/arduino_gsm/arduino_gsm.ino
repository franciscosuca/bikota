

const char apn[]      = "web.vodafone.de";
const char gprsUser[] = "vodafone";
const char gprsPass[] = "vodafone";

const char server[] = "req.dev.iota.pw";
const int  port = 80;

// TTGO T-Call pins
#define MODEM_RST            5
#define MODEM_PWKEY          4
#define MODEM_POWER_ON       23
#define MODEM_TX             27
#define MODEM_RX             26
#define I2C_SDA              21
#define I2C_SCL              22
#define BTN                  15

// Set serial for debug console (to Serial Monitor, default speed 115200)
#define SerialMon Serial
// Set serial for AT commands (to SIM800 module)
#define SerialAT Serial1

// Configure TinyGSM library
#define TINY_GSM_MODEM_SIM800      // Modem is SIM800
#define TINY_GSM_RX_BUFFER   1024  // Set RX buffer to 1Kb

// Define the serial console for debug prints, if needed
//#define DUMP_AT_COMMANDS

#include <Wire.h>
#include <TinyGsmClient.h>

#ifdef DUMP_AT_COMMANDS
#include <StreamDebugger.h>
StreamDebugger debugger(SerialAT, SerialMon);
TinyGsm modem(debugger);
#else
TinyGsm modem(SerialAT);
#endif


// I2C for SIM800 (to keep it running when powered from battery)
TwoWire I2CPower = TwoWire(0);

// TinyGSM Client for Internet connection
TinyGsmClient client(modem);


#define IP5306_ADDR          0x75
#define IP5306_REG_SYS_CTL0  0x00

bool setPowerBoostKeepOn(int en) {
  I2CPower.beginTransmission(IP5306_ADDR);
  I2CPower.write(IP5306_REG_SYS_CTL0);
  if (en) {
    I2CPower.write(0x37); // Set bit1: 1 enable 0 disable boost keep on
  } else {
    I2CPower.write(0x35); // 0x37 is default reg value
  }
  return I2CPower.endTransmission() == 0;
}




void setup() {
  // Set serial monitor debugging window baud rate to 115200
  SerialMon.begin(115200);

  // Start I2C communication
  I2CPower.begin(I2C_SDA, I2C_SCL, 400000);

  // Keep power when running from battery
  bool isOk = setPowerBoostKeepOn(1);
  SerialMon.println(String("IP5306 KeepOn ") + (isOk ? "OK" : "FAIL"));

  // Set modem reset, enable, power pins
  pinMode(MODEM_PWKEY, OUTPUT);
  pinMode(MODEM_RST, OUTPUT);
  pinMode(MODEM_POWER_ON, OUTPUT);
  digitalWrite(MODEM_PWKEY, LOW);
  digitalWrite(MODEM_RST, HIGH);
  digitalWrite(MODEM_POWER_ON, HIGH);
  pinMode(MODEM_PWKEY, INPUT_PULLUP);

  // Set GSM module baud rate and UART pins
  SerialAT.begin(115200, SERIAL_8N1, MODEM_RX, MODEM_TX);
  delay(3000);

  // Restart SIM800 module, it takes quite some time
    // To skip it, call init() instead of restart()
    SerialMon.println("Initializing modem...");
    modem.restart();
    // use modem.init() if you don't need the complete restart
}





void loop() {
  //if (digitalRead(BTN) == 0) {
    //make_request();
    
    SerialMon.print("Connecting to APN: ");
    SerialMon.print(apn);
    if (!modem.gprsConnect(apn, gprsUser, gprsPass)) {
      SerialMon.println(" fail");
    }
    else {
      SerialMon.println(" OK");

      SerialMon.print("Connecting to ");
      SerialMon.print(server);
      if (!client.connect(server, port)) {
        SerialMon.println(" fail");
      }
      else {
        SerialMon.println(" OK");

        // Making an HTTP POST request
        //SerialMon.println("Performing HTTP POST request...");
        // Prepare your HTTP POST request data (Temperature in Celsius degrees)
        //String httpRequestData = "api_key=" + apiKeyValue + "&value1=" + String(bme.readTemperature())
        //                       + "&value2=" + String(bme.readHumidity()) + "&value3=" + String(bme.readPressure()/100.0F) + "";
        // Prepare your HTTP POST request data (Temperature in Fahrenheit degrees)
        //String httpRequestData = "api_key=" + apiKeyValue + "&value1=" + String(1.8 * bme.readTemperature() + 32)
        //                       + "&value2=" + String(bme.readHumidity()) + "&value3=" + String(bme.readPressure()/100.0F) + "";

        String httpRequestData = "api_key=tPmAT5Ab3j7F9&value1=24.75&value2=49.54&value3=1005.14";

        client.print(String("POST ") + "" + " HTTP/1.1\r\n");
        client.print(String("Host: ") + "https://req.dev.iota.pw" + "\r\n");
        client.println("Connection: close");
        //client.println("Content-Type: application/x-www-form-urlencoded");
        client.println("Content-Type: Content-Type: application/json");
        client.print("Content-Length: ");
        client.println(httpRequestData.length());
        client.println();
        client.println(httpRequestData);

        unsigned long timeout = millis();
        while (client.connected() && millis() - timeout < 10000L) {
          // Print available data (HTTP response from server)
          while (client.available()) {
            char c = client.read();
            SerialMon.print(c);
            timeout = millis();
          }
        }
        SerialMon.println();

        // Close client and disconnect
        client.stop();
        SerialMon.println(F("Server disconnected"));
        modem.gprsDisconnect();
        SerialMon.println(F("GPRS disconnected"));
      }
    }
    // Put ESP32 into deep sleep mode (with timer wake up)
    //esp_deep_sleep_start();
 /// }
  delay(30000);
}


void make_request() {
  SerialMon.print("Connecting to APN: ");
  SerialMon.print(apn);
  if (!modem.gprsConnect(apn, gprsUser, gprsPass)) {
    SerialMon.println(" fail");
  }
  else {
    SerialMon.println(" OK");

    SerialMon.print("Connecting to ");
    SerialMon.print(server);
    if (!client.connect(server, port)) {
      SerialMon.println(" fail");
    }
    else {
      SerialMon.println(" OK");

      // Making an HTTP POST request
      //SerialMon.println("Performing HTTP POST request...");
      // Prepare your HTTP POST request data (Temperature in Celsius degrees)
      //String httpRequestData = "api_key=" + apiKeyValue + "&value1=" + String(bme.readTemperature())
      //                       + "&value2=" + String(bme.readHumidity()) + "&value3=" + String(bme.readPressure()/100.0F) + "";
      // Prepare your HTTP POST request data (Temperature in Fahrenheit degrees)
      //String httpRequestData = "api_key=" + apiKeyValue + "&value1=" + String(1.8 * bme.readTemperature() + 32)
      //                       + "&value2=" + String(bme.readHumidity()) + "&value3=" + String(bme.readPressure()/100.0F) + "";

      String httpRequestData = "api_key=tPmAT5Ab3j7F9&value1=24.75&value2=49.54&value3=1005.14";

      client.print(String("POST ") + "" + " HTTP/1.1\r\n");
      client.print(String("Host: ") + "https://req.dev.iota.pw" + "\r\n");
      client.println("Connection: close");
      //client.println("Content-Type: application/x-www-form-urlencoded");
      client.println("Content-Type: Content-Type: application/json");
      client.print("Content-Length: ");
      client.println(httpRequestData.length());
      client.println();
      client.println(httpRequestData);

      unsigned long timeout = millis();
      while (client.connected() && millis() - timeout < 10000L) {
        // Print available data (HTTP response from server)
        while (client.available()) {
          char c = client.read();
          SerialMon.print(c);
          timeout = millis();
        }
      }
      SerialMon.println();

      // Close client and disconnect
      client.stop();
      SerialMon.println(F("Server disconnected"));
      modem.gprsDisconnect();
      SerialMon.println(F("GPRS disconnected"));
    }
  }
  // Put ESP32 into deep sleep mode (with timer wake up)
  //esp_deep_sleep_start();
}