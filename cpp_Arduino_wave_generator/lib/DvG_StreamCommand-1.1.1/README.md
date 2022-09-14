# DvG_StreamCommand ![Latest release](https://img.shields.io/github/v/release/Dennis-van-Gils/DvG_StreamCommand) [![Build Status](https://travis-ci.com/Dennis-van-Gils/DvG_StreamCommand.svg?branch=main)](https://app.travis-ci.com/github/Dennis-van-Gils/DvG_StreamCommand) [![License:MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://github.com/Dennis-van-Gils/DvG_StreamCommand/blob/master/LICENSE.txt) [![Documentation](https://img.shields.io/badge/Docs-Doxygen-blue)](https://dennis-van-gils.github.io/DvG_StreamCommand)

A lightweight Arduino library to listen for commands over a stream.

It provides two classes to allow listening to a stream, such as Serial or Wire, for incoming commands (or data packets in general) and act upon them. Class `DvG_StreamCommand` will listen for ASCII commands, while class `DvG_BinaryStreamCommand` will listen for binary commands.

The API documentation and examples can be found here: https://dennis-van-gils.github.io/DvG_StreamCommand