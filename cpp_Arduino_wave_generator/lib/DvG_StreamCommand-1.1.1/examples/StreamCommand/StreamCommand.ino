/** @example StreamCommand.ino

Listen to the serial port for ASCII commands and act upon them.

An ASCII command is any string ending with a newline '\\n' character.

The following demo commands exist:
  - 'on'       : Turn onboard LED on.
  - 'off'      : Turn onboard LED off.
  - 'set ##.##': Print the passed value back to the terminal, interpreted as a
float, integer and boolean.
*/

#include "DvG_StreamCommand.h"
#include <Arduino.h>

// Instantiate serial port listener for receiving ASCII commands
const uint8_t CMD_BUF_LEN = 16;  // Length of the ASCII command buffer
char cmd_buf[CMD_BUF_LEN]{'\0'}; // The ASCII command buffer
DvG_StreamCommand sc(Serial, cmd_buf, CMD_BUF_LEN);

void setup() {
  Serial.begin(9600);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
}

void loop() {
  // Poll the Serial stream for incoming characters and check if a new
  // completely received command is available
  if (sc.available()) {
    // A new command is available --> Get it and act upon it
    char *str_cmd = sc.getCommand();

    Serial.print("Received: ");
    Serial.println(str_cmd);

    if (strcmp(str_cmd, "on") == 0) {
      Serial.println(" -> LED ON");
      digitalWrite(PIN_LED, HIGH);

    } else if (strcmp(str_cmd, "off") == 0) {
      Serial.println(" -> LED OFF");
      digitalWrite(PIN_LED, LOW);

    } else if (strncmp(str_cmd, "set", 3) == 0) {
      Serial.print(" As float  : ");
      Serial.println(parseFloatInString(str_cmd, 3));
      Serial.print(" As integer: ");
      Serial.println(parseIntInString(str_cmd, 3));
      Serial.print(" As boolean: ");
      Serial.println(parseBoolInString(str_cmd, 3) ? "true" : "false");

    } else {
      Serial.println(" Unknown command");
    }

    Serial.println("");
  }
}