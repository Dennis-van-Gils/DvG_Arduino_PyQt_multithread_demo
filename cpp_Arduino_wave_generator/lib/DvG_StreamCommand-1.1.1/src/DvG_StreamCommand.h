/**
 * @file DvG_StreamCommand.h
 * @author Dennis van Gils (vangils.dennis@gmail.com)
 * @brief A lightweight Arduino library to listen to a stream, such as Serial or
 * Wire, for incoming commands (or data packets in general) and act upon them.
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef DVG_STREAMCOMMAND_H_
#define DVG_STREAMCOMMAND_H_

#include <Arduino.h>

/*******************************************************************************
  DvG_StreamCommand
*******************************************************************************/

/**
 * @brief Class to manage listening to a stream, such as Serial or Wire, for
 * incoming ASCII commands (or ASCII data packets in general) and act upon them.
 *
 * We speak of a completely received 'command' once a linefeed ('\\n', ASCII 10)
 * character is received, or else when the number of incoming characters has
 * exceeded the command buffer size. Carriage return ('\\r', ASCII 13)
 * characters are ignored from the stream.
 *
 * The command buffer is supplied by the user and must be a fixed-size character
 * array (C-string, i.e. '\0' terminated) to store incoming characters into.
 * This keeps the memory usage low and unfragmented, instead of relying on
 * memory hungry C++ strings.
 */
class DvG_StreamCommand {
public:
  /**
   * @brief Construct a new DvG_StreamCommand  object.
   *
   * @param stream Reference to a stream to listen to, e.g. Serial, Wire, etc.
   * @param buffer Reference to the command buffer: A fixed-size character array
   * which will be managed by this class to hold a single incoming command. The
   * buffer should be one character larger than the longest incoming command to
   * allow for the C-string termination character '\0' to become appended.
   * @param max_len Array size of @p buffer including '\0'. Do not exceed the
   * maximum size of 2^^16 = 65536 characters.
   */
  DvG_StreamCommand(Stream &stream, char *buffer, uint16_t max_len);

  /**
   * @brief Poll the stream for incoming characters and append them one-by-one
   * to the command buffer @p buffer. This method should be called repeatedly.
   *
   * @return True when a complete command has been received and is ready to be
   * returned by @ref getCommand(), false otherwise.
   */
  bool available();

  /**
   * @brief Return the reference to the command buffer only when a complete
   * command has been received. Otherwise, an empty C-string is returned.
   *
   * @return char*
   */
  char *getCommand();

  /**
   * @brief Empty the command buffer.
   */
  inline void reset() {
    _fTerminated = false;
    _buffer[0] = '\0';
    _cur_len = 0;
  }

private:
  Stream &_stream;         // Reference to the stream to listen to
  char *_buffer;           // Reference to the command buffer
  uint16_t _max_len;       // Array size of the command buffer
  uint16_t _cur_len;       // Number of currently received command characters
  bool _fTerminated;       // Has a complete command been received?
  const char *_empty = ""; // Empty reply, which is just the '\0' character
};

/*******************************************************************************
  DvG_BinaryStreamCommand
*******************************************************************************/

/**
 * @brief Class to manage listening to a stream, such as Serial or Wire, for
 * incoming binary commands (or binary data packets in general) and act upon
 * them.
 *
 * We speak of a completely received 'command' once a sequence of bytes is
 * received that matches the 'end-of-line' (EOL) sentinel. The EOL sentinel is
 * supplied by the user and should be a single sequence of bytes of fixed length
 * that is unique, i.e. will not appear anywhere inside of the command / data
 * packet that it is suffixing.
 *
 * The command buffer is supplied by the user and must be a fixed-size uint8_t
 * array to store incoming bytes into.
 */
class DvG_BinaryStreamCommand {
public:
  /**
   * @brief Construct a new DvG_BinaryStreamCommand  object.
   *
   * @param stream Reference to a stream to listen to, e.g. Serial, Wire, etc.
   * @param buffer Reference to the command buffer: A fixed-size uint8_t array
   * which will be managed by this class to hold a single incoming command.
   * @param max_len Array size of @p buffer. Do not exceed the maximum size of
   * 2^^16 = 65536 bytes.
   * @param EOL Reference to the end-of-line sentinel: A fixed-size uint8_t
   * array containing a unique sequence of bytes.
   * @param EOL_len Array size of @p EOL. Do not exceed the maximum size of
   * 2^^8 = 256 bytes.
   */
  DvG_BinaryStreamCommand(Stream &stream, uint8_t *buffer, uint16_t max_len,
                          const uint8_t *EOL, uint8_t EOL_len);

  /**
   * @brief Poll the stream for incoming bytes and append them one-by-one to the
   * command buffer @p buffer. This method should be called repeatedly.
   *
   * @param debug_info When true it will print debug information to @p stream
   * as a tab-delimited list of all received bytes in HEX format. WARNING:
   * Enabling this will likely interfere with downstream code listening in to
   * the @p stream for I/O, so use it only for troubleshooting while developing.
   *
   * @return 1 (true) when a complete command has been received and its size is
   * ready to be returned by @ref getCommandLength(). Otherwise 0 (false) when
   * no complete command has been received yet, or -1 (true!) as a special value
   * to indicate that the command buffer was overrun and that the exceeding byte
   * got dropped.
   */
  int8_t available(bool debug_info = false);

  /**
   * @brief Return the length of the command without the EOL sentinel in bytes,
   * only when a complete command has been received. The received command can be
   * read from the user-supplied command buffer up to this length. Otherwise, 0
   * is returned.
   *
   * @return uint16_t
   */
  uint16_t getCommandLength();

  /**
   * @brief Empty the command buffer.
   */
  inline void reset() {
    for (uint16_t i = 0; i < _max_len; ++i) {
      _buffer[i] = 0;
    }
    _found_EOL = false;
    _cur_len = 0;
  }

private:
  Stream &_stream;     // Reference to the stream to listen to
  uint8_t *_buffer;    // Reference to the command buffer
  uint16_t _max_len;   // Array size of the command buffer
  uint16_t _cur_len;   // Number of currently received command bytes
  const uint8_t *_EOL; // Reference to the end-of-line sentinel
  uint16_t _EOL_len;   // Array size of the end-of-line sentinel
  bool _found_EOL;     // Has a complete command been received?
};

/*******************************************************************************
  Parse functions
*******************************************************************************/

/**
 * @brief Safely parse a float value in C-string @p str_in from of position
 * @p pos.
 *
 * @return The parsed float value when successful, 0.0 otherwise.
 */
float parseFloatInString(const char *str_in, uint16_t pos = 0);

/**
 * @brief Safely parse a boolean value in C-string @p str_in from of position
 * @p pos.
 *
 * @return
 *   - False, when @p str_in is empty or @p pos is past the @p str_in length.
 *   - True, when the string perfectly matches 'true', 'True' or 'TRUE'.
 *   - Else, it will interpret the string as an integer, where 0 is considered
 * to be false and all other integers are considered be true. Leading spaces,
 * zeros or signs will be ignored from the integer.
 */
bool parseBoolInString(const char *str_in, uint16_t pos = 0);

/**
 * @brief Safely parse an integer value in C-string @p str_in from of position
 * @p pos.
 *
 * @return The parsed integer value when successful, 0 otherwise.
 */
int parseIntInString(const char *str_in, uint16_t pos = 0);

#endif
