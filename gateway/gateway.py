import socket
import struct
import threading
import time

import os
import can
import isotp

DID_VEHICLE_SPEED = 0xF190
DID_CABIN_TEMP = 0xF191

# DoIP framing constants
DOIP_VERSION = 0x02
DOIP_INVERSE_VERSION = 0xFD
DOIP_PAYLOAD_DIAG_MSG = 0x8001

GW_LOGICAL_ADDR = 0x0E00
SENSOR_LOGICAL_ADDR = 0x0A00
IVI_LOGICAL_ADDR = 0x0B00

SENSOR_HOST = "127.0.0.1"
SENSOR_PORT = 13400

# IVI will connect here
GATEWAY_DOIP_HOST = "0.0.0.0"
GATEWAY_DOIP_PORT = 15000


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


def build_negative_response(request_sid, nrc):
    return bytes([0x7F, request_sid, nrc])


def process_uds_request(uds_request):
    if not uds_request:
        return bytes([0x7F, 0x00, 0x13])  # incorrectMessageLengthOrInvalidFormat

    sid = uds_request[0]

    # Custom update triggers
    if sid == 0x2E and len(uds_request) >= 4:
        did = (uds_request[1] << 8) | uds_request[2]
        if did == 0xF1A1:  # BCM update
            with open("../bcm/data/bcm_update.flag", "w") as f:
                f.write("1")
            return bytes([0x6E, uds_request[1], uds_request[2], uds_request[3]])
        elif did == 0xF1A2:  # IVI update
            with open("../ivi/data/ivi_update.flag", "w") as f:
                f.write("1")
            return bytes([0x6E, uds_request[1], uds_request[2], uds_request[3]])
        elif did == 0xF1A3:  # TCU update
            with open("../tcu/data/tcu_update.flag", "w") as f:
                f.write("1")
            return bytes([0x6E, uds_request[1], uds_request[2], uds_request[3]])

    # Demo gateway supports only ReadDataByIdentifier (0x22)
    if sid != 0x22:
        return build_negative_response(sid, 0x11)  # serviceNotSupported

    # Forward valid request to sensor ECU via DoIP
    try:
        return forward_uds_to_sensor_over_doip(uds_request)
    except Exception as exc:
        print(f"DoIP forward error: {exc}")
        return build_negative_response(sid, 0x7F)


def can_worker():
    bus = can.interface.Bus(channel="vcan0", interface="socketcan")
    addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x7E8,
        rxid=0x7E0
    )
    stack = isotp.CanStack(bus=bus, address=addr)

    print("Gateway CAN worker started on vcan0")

    while True:
        stack.process()
        if stack.available():
            request = stack.recv()
            if not request:
                time.sleep(0.001)
                continue

            print(f"[CAN] RX UDS={request.hex()}")
            response = process_uds_request(request)
            print(f"[CAN] TX UDS={response.hex()}")
            stack.send(response)

        time.sleep(0.001)


def handle_ivi_doip_client(conn, peer):
    print(f"[DoIP] IVI connected: {peer}")
    with conn:
        conn.settimeout(5.0)

        try:
            while True:
                source_addr, target_addr, uds_request = recv_doip_diag_uds(conn)
                print(
                    f"[DoIP] RX src=0x{source_addr:04X} dst=0x{target_addr:04X} uds={uds_request.hex()}"
                )

                if target_addr != GW_LOGICAL_ADDR:
                    sid = uds_request[0] if uds_request else 0x00
                    uds_response = build_negative_response(sid, 0x31)  # requestOutOfRange
                else:
                    uds_response = process_uds_request(uds_request)

                response_frame = build_doip_diag_frame(
                    GW_LOGICAL_ADDR,
                    source_addr,
                    uds_response,
                )
                conn.sendall(response_frame)
                print(
                    f"[DoIP] TX src=0x{GW_LOGICAL_ADDR:04X} dst=0x{source_addr:04X} uds={uds_response.hex()}"
                )

        except (ConnectionError, socket.timeout):
            print(f"[DoIP] IVI disconnected: {peer}")
        except Exception as exc:
            print(f"[DoIP] IVI client error {peer}: {exc}")


def doip_server_worker():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((GATEWAY_DOIP_HOST, GATEWAY_DOIP_PORT))
        server.listen(5)
        print(f"Gateway DoIP server listening on {GATEWAY_DOIP_HOST}:{GATEWAY_DOIP_PORT} for IVI")

        while True:
            conn, peer = server.accept()
            threading.Thread(target=handle_ivi_doip_client, args=(conn, peer), daemon=True).start()


def main():
    # Keep existing CAN path and add DoIP path for IVI in parallel
    threading.Thread(target=can_worker, daemon=True).start()
    threading.Thread(target=doip_server_worker, daemon=True).start()

    print("Gateway started: CAN<->Sensor bridge + IVI over DoIP enabled.")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()