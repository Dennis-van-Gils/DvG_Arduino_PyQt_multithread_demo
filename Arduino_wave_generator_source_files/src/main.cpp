/*******************************************************************************
  Dennis van Gils
  22-08-2018
 ******************************************************************************/

#include <Arduino.h>
#include <math.h>
#include "DvG_SerialCommand.h"

// Serial   : Programming USB port
// SerialUSB: Native USB port. Baudrate setting gets ignored and is always as
//            fast as possible.
#define Ser Serial

// Initiate serial command listener
DvG_SerialCommand sc(Ser);

/*------------------------------------------------------------------------------
    Setup
------------------------------------------------------------------------------*/

void setup() {
  Ser.begin(115200);
}

/*------------------------------------------------------------------------------
    Loop
------------------------------------------------------------------------------*/

#define WAVE_SINE     1
#define WAVE_SQUARE   2
#define WAVE_SAWTOOTH 3

uint8_t wave_type = WAVE_SINE;
double  wave_freq = 0.3;   // [Hz]
double  wave = 0.0;

uint32_t curMillis  = millis();
uint32_t prevMillis = 0;

void loop() {
  char* strCmd; // Incoming serial command string

  // Generate wave sample every millisecond
  curMillis = millis();
  if (curMillis - prevMillis >= 1) {
    
    if (wave_type == WAVE_SINE) {
      wave = sin(2*PI*wave_freq*curMillis/1e3);
    } else if (wave_type == WAVE_SQUARE) {
      wave = (fmod(wave_freq*curMillis/1e3, (double)(1.0)) > 0.5) ? 1 : -1;
    } else if (wave_type == WAVE_SAWTOOTH) {
      wave = 2*fmod(wave_freq*curMillis/1e3, (double)(1.0)) - 1;
    }

    prevMillis = curMillis;
  }

  // Process serial commands
  if (sc.available()) {
    strCmd = sc.getCmd();

    if (strcmp(strCmd, "id?") == 0) {
      Ser.println("Wave generator");
    
    } else if(strcmp(strCmd, "sine") == 0) {
      wave_type = WAVE_SINE;
    } else if(strcmp(strCmd, "square") == 0) {
      wave_type = WAVE_SQUARE;
    } else if(strcmp(strCmd, "sawtooth") == 0) {
      wave_type = WAVE_SAWTOOTH;

    } else if(strcmp(strCmd, "?") == 0) {
      Ser.print(curMillis);
      Ser.print('\t');
      Ser.println(wave, 4);
    }
  }
}
