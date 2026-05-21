# Motor Library Implementation guide

The current plan is to base our new motor library off of the old motor library that we use here is the link to it.

[Library](https://github.com/2b-t/myactuator_rmd)

The structure is as follows.

```
.
├── bindings
│   └── myactuator_rmd.cpp
├── cmake
│   ├── Config.cmake.in
│   └── CTestCustom.cmake.in
├── CMakeLists.txt
├── doc
│   └── Setup.md
├── include
│   └── myactuator_rmd/
├── License.md
├── myactuator_rmd
│   └── __init__.py
├── package.xml
├── ReadMe.md
├── setup.cfg
├── setup.py
├── src
│   ├── actuator_interface.cpp
│   ├── can.
│   └── protocol/
└── test
    ├── actuator_test.cpp
    ├── can/
    ├── can_node.cpp
    ├── mock/
    ├── protocol/
    └── run_tests.cpp

```

## In depth

> [!Bindings]
> Bindings contains one file a C++ file which manually goes and defines all of the bindings to be added into python.

> [!cmake]
> The cmake folder contains a few CMake files which lets us do things like `find_package(myactuator_rmd)` treating it as an object we can include in other build chains. Additionally allowing us to use the project in `CTest`.

> [!doc]
> literally just one markdown file which contains the setup, bad docs.

> [!include]
> Contains all of the headers for the different function definitions, as well as the specific definitions of IO of different classes and objects. The main thing that this include folder does well is storing all of the important information about the protocol such as the command indexes, headers and error bits.

> [!myactuator_rmd]
> This is the folder which stores the python bindings to be installed via `pip` or `pip3` into your python environment, calling `pip3 install -e .` on the folder after a build links this into your python environment

> [!src]
> Contains the actual source code, there is not much overall code however, the actual source
> code in this file is only 688 lines of code, there is not much implementation overall.

> [!test]
> This contains tests using the Google test protocol `gtest`. We will use something similar in our CI/CD

### Overview

The documentation sucks. There is one readme that only talks about the setup and the logging is lackluster. Additionally in the bindings folder there is one file that defines all of the python bindings and it does it completely manually by hand. So heres the improvements i want to make with the new motor library.

# Our own implementation

## Overview:

For our own implementation heres some things to keep in mind, there are 2 seperate motor protocols we can use, Servo mode and MIT mode. Here is the breakdown of each individual one

### Servo mode.

Servo mode is somewhat simple, the first 4 bytes of the can frame are the extended CAN id frame. Heres what the ID frame looks like.

- Bytes[28]->[8] correspond to the command ID bit (EX: 4 means control position so 4<<8 in a int32_t corresponds to that command)
- Bytes[7]->[0] correspond to the motor id (EX: a motor with CAN id 1 will be 1 in a int32_t)

![[Pasted image 20260520152004.png]]

Why 29 bits? Cubemars uses the extended CAN frame from the VESC open motor architecture, if you want to learn more about it go here there is more technical details here but the gist is that this is a open source motor architecture which is widely adopted for its performant and robust use case, [Link to architecture here](https://vesc-project.com/).

The rest of the CAN frame is usually data bits/control bits. The rest of the can frames are usually followed by 7 bytes, which are used to send data back or to send data from the motors. It depends on the commands and i will include a doc that sumarizes all of the commands in a future commit.

> [!Note]
> ID bits can be stored in one continuous int32, you do not need to shift the entire can frame to the left to get it to work, the hardware is smart enough to strip away the empty bits.

## Enabling servo mode

To enable servo mode we have to use their "proprietary" motor firmware version.
**Using the CubeMars Tool:**

> [!Instructions]
>
> 1.  Connect your motor to your computer using the R-LINK and open the CubeMars software.
> 2.  Navigate to the **Mode Switch** tab on the main menu.
> 3.  At the bottom right of this screen, click the **"Servo App"** button to command the driver board to enter Servo mode.

## MIT mode

MIT mode is much similar, but the CAN frames are meant to be used in different way. MIT mode is designed to be much simpler and requires a few can frames to be sent to enable MIT mode. MIT mode packs the bytes super tight and only uses one can frame. Here is the breakdown. To enable MIT mode you need to send the address as the first 11 bytes and then send these following CAN frames.

- Enter motor control mode (enable) `{ADDRESS_BIT_HIGH, ADDRESS_BIT_LOW} {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC}`
- **Exit Motor Control Mode:** Send the data payload `{ADDRESS_BIT_HIGH, ADDRESS_BIT_LOW} {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFD}`
- **Set Current Position to 0:** Send the data payload `{ADDRESS_BIT_HIGH, ADDRESS_BIT_LOW} 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE}`

MIT mode canframes are meant to be extremely compact, you are meant to send commands to it hundreds of times per second down the CAN line. The motors reply with their current information 500 times per second and are meant to be used in highly optimized situations. We can choose to use this in our Drivebase design but this is a discussion for the future.

And then from there the rest of the can frame structure looks like so.

> [!CAN send frame]
> `Data[0]` Motor position << 8 (Motor position high bit)
> `Data[1]` Motor position (Motor position low bit)
> `Data[2]` Motor speed << 8 (Motor speed high)
> `Data[3]` Motor speed low in bits 7->4 in KP value high in bits 3->0
> `Data[4]` KP value (KP value low byte)
> `Data[5]` KD value high
> `Data[6]` KD value low in bytes 7->4 and current value high in bits 3->0
> `Data[7]` Current value low

Motor position is an `int16` every other data value is an `int12` in MIT mode.

> [!CAN response frame]
> `Data[0]` Drive ID number (Motor can ID)
> `Data[1]` Motor position high
> `Data[2]` Motor Position low
> `Data[3]` Motor speed high
> `Data[4]` Motor speed low from bits 7->4 and Current high bits 3->0
> `Data[5]` Current low
> `Data[6]` Motor temperaturew
> `Data[7]` Motor error byte

We control the motor by sending the `send` frame and filling out the specific values, if we want to use this mode we should consider the way we design the controller, `in MIT mode the CAN response frames continuously they are not a send and response thing so we should keep that in mind for what we decide in the future.`

# Implementation

We should aim to keep each part of the implementation as seperate as possible, sending information down the can line as well as different command bits and such should only be accessed where they need to be accessed. I will provide the different command bytes in another doc but for now this is the basic implementation information that you will need to begin
working on the library.

Additionally I aim to have this be treated as a ROS package, which means defining a package.xml and following the documentation for ROS's build system `colcon` to make this much easier to pull into ROS packages.

# Future considerations (for the drivebase node)

We are going to be developing for 2 separate communication modes, so we need to be able to differentiate between. However some things to keep in mind for our future drivebase implementation is MIT mode can be turned on using some can frames we can control, Servo mode has a more convoluted setup that may cause issues in the future.
