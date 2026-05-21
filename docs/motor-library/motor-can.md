# Can frames

### Command ID 0: Duty Cycle Mode

**Description:** Sets a specified duty cycle voltage for the motor.

**Bytes Used:** 4 bytes (pad remaining 4 with `0x00`)

**Data Type:** 32-bit Integer (`int32_t`)

**Scaling:** Multiply float duty cycle by `100000.0` (Range: 0 to 100,000)

| **Byte Index** | **Field**         | **Description**                     |
| -------------- | ----------------- | ----------------------------------- |
| **Data[0]**    | Duty Cycle        | Highest 8 bits of 32-bit duty cycle |
| **Data[1]**    | Duty Cycle        | Upper middle 8 bits                 |
| **Data[2]**    | Duty Cycle [15:8] | Lower middle 8 bits                 |
| **Data[3]**    | Duty Cycle [7:0]  | Lowest 8 bits                       |
| **Data[4-7]**  | Unused            | Send as `0x00`                      |

### Command ID 1: Current Loop Mode

**Description:** Sets a specified Iq current for the motor (Torque control).

**Bytes Used:** 4 bytes (pad remaining 4 with `0x00`)

**Data Type:** 32-bit Integer (`int32_t`)

**Scaling:** Multiply float current (Amps) by `1000.0` (Range: -60,000 to 60,000)

| **Byte Index** | **Field**      | **Description**                         |
| -------------- | -------------- | --------------------------------------- |
| **Data[0]**    | Current        | Highest 8 bits of 32-bit target current |
| **Data[1]**    | Current        | Upper middle 8 bits                     |
| **Data[2]**    | Current [15:8] | Lower middle 8 bits                     |
| **Data[3]**    | Current [7:0]  | Lowest 8 bits                           |
| **Data[4-7]**  | Unused         | Send as `0x00`                          |

### Command ID 2: Current Brake Mode

**Description:** Applies a holding braking current to the motor.

**Bytes Used:** 4 bytes (pad remaining 4 with `0x00`)

**Data Type:** 32-bit Integer (`int32_t`)

**Scaling:** Multiply float current (Amps) by `1000.0` (Range: 0 to 60,000)

| **Byte Index** | **Field**            | **Description**                        |
| -------------- | -------------------- | -------------------------------------- |
| **Data[0]**    | Brake Current        | Highest 8 bits of 32-bit brake current |
| **Data[1]**    | Brake Current        | Upper middle 8 bits                    |
| **Data[2]**    | Brake Current [15:8] | Lower middle 8 bits                    |
| **Data[3]**    | Brake Current [7:0]  | Lowest 8 bits                          |
| **Data[4-7]**  | Unused               | Send as `0x00`                         |

### Command ID 3: Velocity Loop Mode

**Description:** Sets a continuous target operating speed (ERPM).

**Bytes Used:** 4 bytes (pad remaining 4 with `0x00`)

**Data Type:** 32-bit Integer (`int32_t`)

**Scaling:** Send ERPM directly as an integer (Range: -100,000 to 100,000)

| **Byte Index** | **Field**       | **Description**                       |
| -------------- | --------------- | ------------------------------------- |
| **Data[0]**    | Velocity        | Highest 8 bits of 32-bit target speed |
| **Data[1]**    | Velocity        | Upper middle 8 bits                   |
| **Data[2]**    | Velocity [15:8] | Lower middle 8 bits                   |
| **Data[3]**    | Velocity [7:0]  | Lowest 8 bits                         |
| **Data[4-7]**  | Unused          | Send as `0x00`                        |

### Command ID 4: Position Loop Mode

**Description:** Moves the motor to a specific target angle at maximum speed.

**Bytes Used:** 4 bytes (pad remaining 4 with `0x00`)

**Data Type:** 32-bit Integer (`int32_t`)

**Scaling:** Multiply float position (Degrees) by `10000.0` (Range: -360,000,000 to 360,000,000)

| **Byte Index** | **Field**       | **Description**                          |
| -------------- | --------------- | ---------------------------------------- |
| **Data[0]**    | Position        | Highest 8 bits of 32-bit target position |
| **Data[1]**    | Position        | Upper middle 8 bits                      |
| **Data[2]**    | Position [15:8] | Lower middle 8 bits                      |
| **Data[3]**    | Position [7:0]  | Lowest 8 bits                            |
| **Data[4-7]**  | Unused          | Send as `0x00`                           |

### Command ID 5: Set Origin Mode

**Description:** Sets the current physical position of the motor as the new zero-degree origin. **Bytes Used:** 1 byte (pad remaining 7 with `0x00`) **Data Type:** 8-bit Integer (`uint8_t`) **Parameters:** `0x00` = Temporary Origin (clears on power loss). `0x01` = Permanent Origin (only for dual encoder models).

| **Byte Index** | **Field**   | **Description**                          |
| -------------- | ----------- | ---------------------------------------- |
| **Data[0]**    | Set Command | `0x00` (Temporary) or `0x01` (Permanent) |
| **Data[1-7]**  | Unused      | Send as `0x00`                           |

### Command ID 6: Position-Velocity Loop Mode

**Description:** Moves the motor to a target position adhering to strict speed and acceleration limits.

**Bytes Used:** 8 bytes (Fully packed)

**Data Types & Scaling:** \* **Position:** `int32_t` (Multiply degrees by `10000.0`)

- **Speed:** `int16_t` (Divide ERPM by `10.0`)
- **Acceleration:** `int16_t` (Divide ERPM/s² by `10.0`)

| **Byte Index** | **Field**           | **Description**                             |
| -------------- | ------------------- | ------------------------------------------- |
| **Data[0]**    | Position            | Highest 8 bits of 32-bit target position    |
| **Data[1]**    | Position            | Upper middle 8 bits                         |
| **Data[2]**    | Position [15:8]     | Lower middle 8 bits                         |
| **Data[3]**    | Position [7:0]      | Lowest 8 bits                               |
| **Data[4]**    | Speed [15:8]        | Highest 8 bits of 16-bit speed limit        |
| **Data[5]**    | Speed [7:0]         | Lowest 8 bits of 16-bit speed limit         |
| **Data[6]**    | Acceleration [15:8] | Highest 8 bits of 16-bit acceleration limit |
| **Data[7]**    | Acceleration [7:0]  | Lowest 8 bits of 16-bit acceleration limit  |
