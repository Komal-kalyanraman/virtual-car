import socket
import struct
import time
import isotp
import can

DID_VEHICLE_SPEED = 0xF190
DID_CABIN_TEMP = 0xF191

# Minimal DoIP framing constants (ISO 13400 style header)
DOIP_VERSION = 0x02
DOIP_INVERSE_VERSION = 0xFD
DOIP_PAYLOAD_DIAG_MSG = 0x8001

GW_LOGICAL_ADDR = 0x0E00
SENSOR_LOGICAL_ADDR = 0x0A00
SENSOR_HOST = "127.0.0.1"
SENSOR_PORT = 13400

def build_doip_diag_frame(source_addr, target_addr, uds_payload):
    payload = struct.pack("!HH", source_addr, target_addr) + uds_payload
    header = struct.pack(
        "!BBHI",
        DOIP_VERSION,
        DOIP_INVERSE_VERSION,
        DOIP_PAYLOAD_DIAG_MSG,
        len(payload),
    )
    return header + payload


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Socket closed while reading DoIP frame")
        data += chunk
    return data


def recv_doip_diag_uds(sock):
    header = recv_exact(sock, 8)
    version, inverse_version, payload_type, payload_len = struct.unpack("!BBHI", header)
    if version != DOIP_VERSION or inverse_version != DOIP_INVERSE_VERSION:
        raise ValueError("Invalid DoIP version")
    if payload_type != DOIP_PAYLOAD_DIAG_MSG:
        raise ValueError(f"Unsupported DoIP payload type: 0x{payload_type:04X}")

    payload = recv_exact(sock, payload_len)
    if len(payload) < 4:
        raise ValueError("DoIP diagnostic payload too short")

    source_addr, target_addr = struct.unpack("!HH", payload[:4])
    uds_payload = payload[4:]
    return source_addr, target_addr, uds_payload


def forward_uds_to_sensor_over_doip(uds_request):
    with socket.create_connection((SENSOR_HOST, SENSOR_PORT), timeout=1.0) as sock:
        sock.settimeout(1.0)
        frame = build_doip_diag_frame(GW_LOGICAL_ADDR, SENSOR_LOGICAL_ADDR, uds_request)
        sock.sendall(frame)
        _, _, uds_response = recv_doip_diag_uds(sock)
        return uds_response

def main():
    bus = can.interface.Bus(channel="vcan0", interface="socketcan")
    addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x7E8,
        rxid=0x7E0
    )
    stack = isotp.CanStack(bus=bus, address=addr)

    print(
        f"CAN-to-DoIP gateway running. CAN=vcan0, DoIP target={SENSOR_HOST}:{SENSOR_PORT}"
    )

    while True:
        stack.process()
        if stack.available():
            request = stack.recv()
            print(f"Received CAN data: {request.hex()}")

            if request and len(request) >= 3 and request[0] == 0x22:
                try:
                    response = forward_uds_to_sensor_over_doip(request)
                except Exception as exc:
                    print(f"DoIP forward error: {exc}")
                    # Service not supported in active session -> used here for transport failure
                    response = bytes([0x7F, request[0], 0x7F])

                print(f"Sending CAN data: {response.hex()}")
                stack.send(response)
            elif request:
                # Request out of range for this demo gateway
                response = bytes([0x7F, request[0], 0x11])
                print(f"Sending CAN data: {response.hex()}")
                stack.send(response)
        time.sleep(0.001)

if __name__ == "__main__":
    main()