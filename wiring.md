# Spotifoni Wiring

![Schematic](spotifoni%20schematic.png)

## GPIO Allocation

| Function | GPIO Pins | Header Pins |
|---|---|---|
| Encoder 1 — Volume | GPIO 17, 27, 22 | 11, 13, 15 |
| Encoder 2 — Previous | GPIO 5, 6, 13 | 29, 31, 33 |
| Encoder 3 — Play/Pause | GPIO 23, 24, 25 | 16, 18, 22 |
| Encoder 4 — Next | GPIO 12, 16, 26 | 32, 36, 37 |
| WS2812B LED data | GPIO 10 | 19 |
| SPI0 (reserved by driver) | GPIO 7, 8, 9, 11 | 26, 24, 21, 23 |
| *I²S bus (allocated)* | GPIO 18, 19, 21 | 12, 35, 40 |

## I²S Amplifier (U1 — MAX98357A)

| Pi Header | Function | MAX98357A |
|---|---|---|
| Pin 2 | 5V Power | VDD |
| Pin 6 | Ground | GND |
| Pin 12 | GPIO 18 · PCM_CLK | BCLK |
| Pin 35 | GPIO 19 · PCM_FS | LRCLK |
| Pin 40 | GPIO 21 · PCM_DOUT | DIN |

Speaker output (OUTP/OUTN) connects to a Visaton FR 10 HM 8Ω speaker.

## WS2812B LED Display (D1–D4)

The LED data signal passes through a logic level converter (U2) to shift GPIO 10's 3.3V output to 5V. A 1kΩ resistor (R1) sits between the level converter output and the first LED's DIN pin.

| From | To | Notes |
|---|---|---|
| Pi GPIO 10 (Pin 19) | U2 LV1 (pin 1) | 3.3V data from SPI MOSI |
| U2 HV1 (pin 12) | R1 (470Ω) → D1 WS2812B DIN | 5V level-shifted data out |
| Pi 3.3V (Pin 1) | U2 LVCC (pin 3) | Level converter low-side supply |
| 5V rail | U2 HVCC (pin 9) | Level converter high-side supply |
| GND | U2 LVSS (pin 5), U2 HVSS (pin 4) | Common ground |
| 5V rail | C1 1000µF cap (+) → D1 VDD | Bulk decoupling for LED chain |
| GND | C1 1000µF cap (−) → D1 VSS | |

LEDs are daisy-chained: D1 DOUT → D2 DIN → D3 DIN → D4 DIN. Each LED's VDD connects to 5V and VSS to GND.

## Encoder Wiring (J2–J5)

All four encoders use the same wiring pattern. Connect each encoder's `+` pin to **3.3V** and `GND` to ground. The CLK, DT, and SW pins connect to the GPIO pins listed in the allocation table above.

| KY-040 Pin | Connects To | Notes |
|---|---|---|
| + | Pi 3.3V (Pin 1) | **Not 5V** — Pi GPIOs are 3.3V only |
| GND | Pi GND | Shared ground rail |
| CLK (A) | GPIO per table | Quadrature channel A |
| DT (B) | GPIO per table | Quadrature channel B |
| SW | GPIO per table | Push button (use internal pull-up) |

## Power Supply

An AC/DC power supply provides 5V to the system through an on/off switch (SW1). The Pi, MAX98357A, level converter high side, and WS2812B LEDs all run from this 5V rail.

## Setup Notes

1. Enable I²S output: add `dtoverlay=hifiberry-dac` to `/boot/firmware/config.txt` and reboot.
2. Enable SPI: add `dtparam=spi=on` to `/boot/firmware/config.txt` and reboot.
3. Test audio: `speaker-test -D hw:0 -t sine`.
4. Connect encoders to **3.3V (Pin 1), not 5V**. Pi GPIO pins are 3.3V-tolerant only — 5V will damage them.
5. The KY-040 has onboard 10kΩ pull-ups on CLK and DT. No external resistors needed. The SW pin uses the Pi's internal pull-up (configured in software).
6. The SPI driver claims GPIO 7, 8, 9, 10, 11 — only GPIO 10 (MOSI) is physically wired.
7. The 470Ω resistor goes between the level converter output and the first LED's DIN pin to protect against voltage spikes during power-on.
8. The 1000µF electrolytic capacitor (6.3V, 20%) goes across the first LED's VDD and GND, as close to D1 as possible.
9. Chain additional LEDs by connecting DOUT of one module to DIN of the next. Update `LED_COUNT` in software to match.
