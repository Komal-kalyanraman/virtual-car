import socket
import struct
import tkinter as tk

DOIP_VERSION = 0x02
DOIP_INVERSE_VERSION = 0xFD
DOIP_PAYLOAD_DIAG_MSG = 0x8001

TCU_LOGICAL_ADDR = 0x0C00
GW_LOGICAL_ADDR = 0x0E00
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 15000

DID_BCM_UPDATE = 0xF1A1  # Custom DID for BCM update
DID_IVI_UPDATE = 0xF1A2  # Custom DID for IVI update

def build_doip_diag_frame(source_addr, target_addr, uds_payload):
    payload = struct.pack("!HH", source_addr, target_addr) + uds_payload
    header = struct.pack("!BBHI", DOIP_VERSION, DOIP_INVERSE_VERSION, DOIP_PAYLOAD_DIAG_MSG, len(payload))
    return header + payload

def send_update_trigger(did, value):
    try:
        with socket.create_connection((GATEWAY_HOST, GATEWAY_PORT), timeout=2.0) as sock:
            sock.settimeout(2.0)
            uds_request = bytes([0x2E, (did >> 8) & 0xFF, did & 0xFF, value])
            frame = build_doip_diag_frame(TCU_LOGICAL_ADDR, GW_LOGICAL_ADDR, uds_request)
            sock.sendall(frame)
            # Read response (ignore content for this demo)
            sock.recv(1024)
    except Exception as e:
        print(f"TCU: Error sending update: {e}")

def main():
    root = tk.Tk()
    root.title("TCU Update Trigger")

    tk.Label(root, text="TCU Update Panel", font=("Arial", 18)).pack(pady=10)

    tk.Button(root, text="Update BCM (100ms → 1 second)", font=("Arial", 14),
              command=lambda: send_update_trigger(DID_BCM_UPDATE, 1)).pack(pady=10)

    tk.Button(root, text="Update IVI (Celsius → Fahrenheit)", font=("Arial", 14),
              command=lambda: send_update_trigger(DID_IVI_UPDATE, 1)).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()