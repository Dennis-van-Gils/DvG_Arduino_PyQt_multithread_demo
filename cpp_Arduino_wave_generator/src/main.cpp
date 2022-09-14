/*******************************************************************************
  Dennis van Gils
  14-09-2022
 ******************************************************************************/

#include <Arduino.h>
#include <math.h>

#include "DvG_StreamCommand.h"

// On the Arduino M0 Pro:
// Serial   : Programming USB port
// SerialUSB: Native USB port. Baudrate setting gets ignored and is always as
//            fast as possible.
#define Ser Serial

// Instantiate serial port listener for receiving ASCII commands
const uint8_t CMD_BUF_LEN = 16;  // Length of the ASCII command buffer
char cmd_buf[CMD_BUF_LEN]{'\0'}; // The ASCII command buffer
DvG_StreamCommand sc(Ser, cmd_buf, CMD_BUF_LEN);

/*------------------------------------------------------------------------------
    Setup
------------------------------------------------------------------------------*/

void setup() { Ser.begin(115200); }

/*------------------------------------------------------------------------------
    Loop
------------------------------------------------------------------------------*/

#define WAVE_SINE 1
#define WAVE_SQUARE 2
#define WAVE_SAWTOOTH 3

uint8_t wave_type = WAVE_SINE;
double wave_freq = 0.3; // [Hz]
double wave = 0.0;

uint32_t curMillis = millis();
uint32_t prevMillis = 0;

void loop() {
  // Generate wave sample every millisecond
  curMillis = millis();
  if (curMillis - prevMillis >= 1) {

    if (wave_type == WAVE_SINE) {
      wave = sin(2 * PI * wave_freq * curMillis / 1e3);
    } else if (wave_type == WAVE_SQUARE) {
      wave = (fmod(wave_freq * curMillis / 1e3, (double)(1.0)) > 0.5) ? 1 : -1;
    } else if (wave_type == WAVE_SAWTOOTH) {
      wave = 2 * fmod(wave_freq * curMillis / 1e3, (double)(1.0)) - 1;
    }

    prevMillis = curMillis;
  }

  // Poll the Serial stream for incoming characters and check if a new
  // completely received command is available
  if (sc.available()) {
    // A new command is available --> Get it and act upon it
    char *str_cmd = sc.getCommand();

    if (strcmp(str_cmd, "id?") == 0) {
      Ser.println("Arduino, Wave generator");

    } else if (strcmp(str_cmd, "sine") == 0) {
      wave_type = WAVE_SINE;
    } else if (strcmp(str_cmd, "square") == 0) {
      wave_type = WAVE_SQUARE;
    } else if (strcmp(str_cmd, "sawtooth") == 0) {
      wave_type = WAVE_SAWTOOTH;

    } else if (strcmp(str_cmd, "?") == 0) {
      Ser.print(curMillis);
      Ser.print('\t');
      Ser.println(wave, 4);
    }
  }
}
