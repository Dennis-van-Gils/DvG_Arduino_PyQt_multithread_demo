# I developed this library using PlatformIO inside VSCode. The folder structure
# required by PlatformIO differs from how an Arduino library package should be
# structured like. Hence, I'll use symbolic file and folder links to 'fool'
# VSCode, such that it can find this libraries' .cpp and .h files and will be
# able to compile the examples.
#
# Dennis van Gils, 29-08-2022

# Windows cmd command:
mklink /H src\main.cpp examples\StreamCommand\StreamCommand.ino

# Or Windows PowerShell:
New-Item -ItemType Junction -Path "src\main.cpp" -Target "examples\StreamCommand\StreamCommand.ino"

# Also, remember to put `.nojekyll` file inside \docs folder, otherwise the
html pages containing the source code will disappear because they start with the
'_' character. Jekyll will filter out files starting with '_'.