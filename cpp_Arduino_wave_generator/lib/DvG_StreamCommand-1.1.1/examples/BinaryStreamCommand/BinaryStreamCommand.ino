/** @example BinaryStreamCommand.ino

Listen to the serial port for binary commands and act upon them.

A binary command is a byte stream ending in a specific order as set by the
end-of-line (EOL) sentinel.

For convenience, this demo has the EOL set to '!!' such that you can type these
ASCII characters in a terminal to terminate the command. This demo will simply
print all received bytes back to the terminal once a complete command has been
received.
*/

#include "DvG_StreamCommand.h"
#include <Arduino.h>

// Instantiate serial port listener for receiving binary commands
const uint8_t BIN_BUF_LEN = 16;     // Length of the binary command buffer
uint8_t bin_buf[BIN_BUF_LEN];       // The binary command buffer
const uint8_t EOL[] = {0x21, 0x21}; // End-of-line sentinel, 0x21 = '!'
DvG_BinaryStreamCommand bsc(Serial, bin_buf, BIN_BUF_LEN, EOL, sizeof(EOL));

void setup() { Serial.begin(9600); }

void loop() {
  // Poll the Serial stream for incoming bytes
  int8_t bsc_available = bsc.available();

  if (bsc_available == -1) {
    Serial.println("Buffer has overrun and bytes got dropped.");
    bsc.reset();

  } else if (bsc_available) {
    // A new command is available --> Get the number of bytes and act upon it
    uint16_t data_len = bsc.getCommandLength();

    // Simply print all received bytes back to the terminal
    Serial.println("Received command bytes:");
    for (uint16_t idx = 0; idx < data_len; ++idx) {
      Serial.print((char)bin_buf[idx]);
      Serial.write('\t');
      Serial.print(bin_buf[idx], DEC);
      Serial.write('\t');
      Serial.println(bin_buf[idx], HEX);
    }
  }
}