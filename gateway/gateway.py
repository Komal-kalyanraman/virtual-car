# import random
# import time
# import threading
# import isotp
# import can

# DID_VEHICLE_SPEED = 0xF190
# DID_CABIN_TEMP = 0xF191

# vehicle_speed = 0
# cabin_temp = 0

# def update_vehicle_speed():
#     global vehicle_speed
#     while True:
#         vehicle_speed = int(random.uniform(100, 150))
#         time.sleep(0.1)

# def update_cabin_temp():
#     global cabin_temp
#     while True:
#         cabin_temp = int(random.uniform(20, 30))
#         time.sleep(3)

# def main():
#     threading.Thread(target=update_vehicle_speed, daemon=True).start()
#     threading.Thread(target=update_cabin_temp, daemon=True).start()

#     bus = can.interface.Bus('vcan0', bustype='socketcan')
#     addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=0x7E8, rxid=0x7E0)
#     stack = isotp.CanStack(bus=bus, address=addr)

#     print("Simulated UDS server running on vcan0...")

#     while True:
#         if stack.available():
#             request = stack.recv()
#             # UDS Service 0x22: ReadDataByIdentifier
#             if request and request[0] == 0x22:
#                 did = (request[1] << 8) | request[2]
#                 if did == DID_VEHICLE_SPEED:
#                     value = vehicle_speed
#                 elif did == DID_CABIN_TEMP:
#                     value = cabin_temp
#                 else:
#                     value = 0
#                 # UDS positive response: 0x62, echo DID, then value (2 bytes)
#                 response = bytes([0x62, request[1], request[2]]) + value.to_bytes(2, 'big')
#                 stack.send(response)
#         time.sleep(0.01)

# if __name__ == "__main__":
#     main()

import random
import time
import threading
import isotp
import can

DID_VEHICLE_SPEED = 0xF190
DID_CABIN_TEMP = 0xF191

vehicle_speed = 0
cabin_temp = 0


def update_vehicle_speed():
    global vehicle_speed
    while True:
        vehicle_speed = int(random.uniform(100, 150))
        time.sleep(0.1)


def update_cabin_temp():
    global cabin_temp
    while True:
        cabin_temp = int(random.uniform(20, 30))
        time.sleep(3)


def main():
    threading.Thread(target=update_vehicle_speed, daemon=True).start()
    threading.Thread(target=update_cabin_temp, daemon=True).start()

    # python-can: use interface instead of deprecated bustype
    bus = can.interface.Bus(channel="vcan0", interface="socketcan")

    # Server receives requests on 0x7E0 and responds on 0x7E8
    addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x7E8,
        rxid=0x7E0
    )
    stack = isotp.CanStack(bus=bus, address=addr)

    print("Simulated UDS server running on vcan0...")

    while True:
        # REQUIRED: process ISO-TP state machine every loop
        stack.process()

        if stack.available():
            request = stack.recv()

            # UDS Service 0x22: ReadDataByIdentifier
            if request and len(request) >= 3 and request[0] == 0x22:
                did = (request[1] << 8) | request[2]

                if did == DID_VEHICLE_SPEED:
                    value = vehicle_speed
                    response = bytes([0x62, request[1], request[2]]) + value.to_bytes(2, "big")
                elif did == DID_CABIN_TEMP:
                    value = cabin_temp
                    response = bytes([0x62, request[1], request[2]]) + value.to_bytes(2, "big")
                else:
                    # Negative response: Request Out Of Range
                    response = bytes([0x7F, 0x22, 0x31])

                stack.send(response)

        # Keep CPU usage reasonable
        time.sleep(0.001)


if __name__ == "__main__":
    main()