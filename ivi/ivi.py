import os
import socket
import struct
import time

DID_CABIN_TEMP = 0xF191

DOIP_VERSION = 0x02
DOIP_INVERSE_VERSION = 0xFD
DOIP_PAYLOAD_DIAG_MSG = 0x8001

IVI_LOGICAL_ADDR = 0x0B00
GW_LOGICAL_ADDR = 0x0E00
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 15000

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
            raise ConnectionError("Socket closed")
        data += chunk
    return data

def recv_doip_diag(sock):
    header = recv_exact(sock, 8)
    version, inverse_version, payload_type, payload_len = struct.unpack("!BBHI", header)
    if version != DOIP_VERSION or inverse_version != DOIP_INVERSE_VERSION:
        raise ValueError("Invalid DoIP version")
    if payload_type != DOIP_PAYLOAD_DIAG_MSG:
        raise ValueError(f"Unsupported payload type: 0x{payload_type:04X}")

    payload = recv_exact(sock, payload_len)
    if len(payload) < 4:
        raise ValueError("Diagnostic payload too short")

    source_addr, target_addr = struct.unpack("!HH", payload[:4])
    uds_payload = payload[4:]
    return source_addr, target_addr, uds_payload

def main():
    show_fahrenheit = False
    while True:
        try:
            with socket.create_connection((GATEWAY_HOST, GATEWAY_PORT), timeout=2.0) as sock:
                sock.settimeout(2.0)
                print(f"Connected to gateway DoIP {GATEWAY_HOST}:{GATEWAY_PORT}")

                while True:
                    # Check for update trigger
                    if os.path.exists("/tmp/ivi_update.flag"):
                        show_fahrenheit = True
                        os.remove("/tmp/ivi_update.flag")
                        print("IVI: Switched to Fahrenheit display due to TCU update trigger.")

                    # UDS ReadDataByIdentifier for cabin temp DID 0xF191
                    uds_request = bytes([0x22, 0xF1, 0x91])
                    frame = build_doip_diag_frame(IVI_LOGICAL_ADDR, GW_LOGICAL_ADDR, uds_request)
                    sock.sendall(frame)

                    source_addr, target_addr, uds_response = recv_doip_diag(sock)

                    ok = (
                        source_addr == GW_LOGICAL_ADDR
                        and target_addr == IVI_LOGICAL_ADDR
                        and len(uds_response) >= 5
                        and uds_response[0] == 0x62
                        and uds_response[1] == 0xF1
                        and uds_response[2] == 0x91
                    )

                    if ok:
                        temp = int.from_bytes(uds_response[3:5], byteorder="big", signed=False)
                        if show_fahrenheit:
                            temp_f = round((temp * 9 / 5) + 32)
                            print(f"Cabin Temperature: {temp_f} F")
                        else:
                            print(f"Cabin Temperature: {temp} C")
                    else:
                        print("Cabin Temperature: --")

                    time.sleep(3)

        except Exception as exc:
            print(f"IVI DoIP error: {exc}")
            print("Cabin Temperature: --")
            time.sleep(1)

if __name__ == "__main__":
    main()