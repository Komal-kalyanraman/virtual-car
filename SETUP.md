# Virtual Car Project

This project simulates a vehicle gateway and IVI (In-Vehicle Infotainment) system communicating over a virtual CAN interface using UDS (Unified Diagnostic Services).

## Prerequisites

- Python 3.8+
- Linux OS (for virtual CAN)
- `python-can`, `python-can-isotp`, and `udsoncan` Python packages

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

```sh
cd ivi
python ivi.py
```

### 7. Installl Tkinter across PC

```sh
sudo apt-get install python3-tk
```
