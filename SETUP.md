# Virtual Car Project

This project simulates a vehicle gateway and IVI (In-Vehicle Infotainment) system communicating over a virtual CAN interface using UDS (Unified Diagnostic Services).

## Prerequisites

- Python 3.8+
- Linux OS (for virtual CAN and native C/C++ clients)
- For Python clients: `python-can`, `python-can-isotp`, and `udsoncan` Python packages
- For native C/C++ clients:
  - GCC (for compiling C/C++ code)
  - Linux kernel headers (for SocketCAN/ISOTP)
  - SocketCAN and ISO-TP kernel modules (`can`, `vcan`, `can-isotp`)
  - `can-utils` package for CAN interface management

## Setup Instructions

### 1. Clone the Repository

```sh
git clone <your-repo-url>
cd virtual-car
```

### 2. Set Up a Python Virtual Environment

```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Python Packages

```sh
pip install python-can
pip install git+https://github.com/pylessard/python-can-isotp.git
pip install udsoncan
```

### 3b. Install Native Client Prerequisites (C/C++)

```sh
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r) can-utils
sudo modprobe can
sudo modprobe vcan
sudo modprobe can-isotp
```

### 4. Set Up the Virtual CAN Interface

```sh
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

### 5. Run the Gateway (UDS Server)

```sh
cd gateway
python gateway.py
```

### 6. Run the IVI (UDS Client)

Open a new terminal, activate the virtual environment, then:

**Python client:**

```sh
cd ivi
python3 ivi.py
```

**Native C client:**

```sh
cd ivi
gcc -std=c17 -Wall -Wextra -o ivi ivi.c
./ivi
```

### 7. Run the BCM (UDS Client)

Open a new terminal:

**Python client:**

```sh
cd bcm
python3 bcm.py
```

**Native C++ client:**

```sh
cd bcm
g++ -std=c++17 -o bcm bcm.cpp -lpthread
sudo ./bcm
```

### 8. Install Tkinter (for TCU UI)

```sh
sudo apt-get install python3-tk
```
