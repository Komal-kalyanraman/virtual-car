# Virtual Car UDS-over-CAN Simulation

This project simulates a vehicle gateway Electronic Control Unit (ECU) and an In-Vehicle Infotainment (IVI) system communicating over a virtual CAN bus using the Unified Diagnostic Services (UDS) protocol. It is designed for learning, prototyping, and validating UDS-over-CAN communication in a way that closely mirrors real automotive hardware and software.

## Project Structure

- **gateway/**: Contains `gateway.py`, which acts as a simulated vehicle gateway ECU (UDS server) providing mock vehicle speed and cabin temperature data.
- **ivi/**: Contains `ivi.py`, which acts as a UDS client (e.g., an IVI or diagnostic tool) requesting and displaying the cabin temperature.
- **bcm/**: (Optional) Can be used for a second client, e.g., to request vehicle speed.
- **SETUP.md**: Step-by-step setup and run instructions.

## Features

- **Realistic UDS-over-CAN stack:** Uses `python-can`, `python-can-isotp`, and `udsoncan` to implement the same protocol layers used in real vehicles.
- **Virtual CAN bus:** Uses Linux’s `vcan0` interface, which emulates a real CAN bus in software—no hardware required.
- **Mock data generation:** The gateway simulates live vehicle speed and cabin temperature, updating at realistic intervals.
- **Threaded server:** The gateway updates signals in real time, just like a real ECU.
- **Standard UDS services:** Implements UDS service 0x22 (ReadDataByIdentifier) with correct positive and negative response formats.

## How Close Is This to Real Hardware?

- **Protocol stack:** The code uses the same CAN, ISOTP, and UDS protocol layers as real automotive ECUs and diagnostic tools.
- **Message format:** UDS messages, DIDs, and responses are byte-for-byte identical to what you’d see on a real CAN bus.
- **Bus interface:** The only difference is the use of `vcan0` (virtual) instead of a physical CAN interface (e.g., `can0` with a USB-CAN adapter). Switching to real hardware is as simple as changing the interface name.
- **Timing and concurrency:** Signal updates and request/response cycles are managed with real Python threads and timers, similar to embedded systems.
- **Scalability:** You can add more ECUs or clients, or connect to real hardware, with minimal code changes.

**Limitations compared to real hardware:**

- No electrical noise, bus errors, or arbitration.
- No security access, session control, or advanced diagnostics (but these can be added).
- No interaction with actual vehicle sensors or actuators.

## Getting Started

See [SETUP.md](SETUP.md) for full setup and run instructions.

## Extending the Project

- Add more DIDs and UDS services to the server.
- Implement additional clients (e.g., for vehicle speed).
- Connect to real CAN hardware by changing `vcan0` to your hardware interface (e.g., `can0`).
