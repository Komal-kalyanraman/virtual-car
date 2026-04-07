import os
import time
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

DID_BCM_UPDATE = 0xF1A1 # BCM update trigger DID
DID_IVI_UPDATE = 0xF1A2 # IVI update trigger DID
DID_TCU_UPDATE = 0xF1A3 # TCU update trigger DID

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
            sock.recv(1024)
    except Exception as e:
        print(f"TCU: Error sending update: {e}")

def main():
    # Remove previous flag files in data folder
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    flag_path = os.path.join(data_dir, "tcu_update.flag")
    if os.path.exists(flag_path):
        os.remove(flag_path)

    root = tk.Tk()
    root.title("TCU Update Trigger")

    tk.Label(root, text="TCU Update Panel", font=("Arial", 18)).pack(pady=10)

    status_label = tk.Label(root, text="", font=("Arial", 12), fg="blue")
    status_label.pack(pady=5)

    bcm_btn = tk.Button(root, text="Update BCM (100ms → 1 second)", font=("Arial", 14),
                        command=lambda: send_update_trigger(DID_BCM_UPDATE, 1))
    bcm_btn.pack(pady=10)

    ivi_btn = tk.Button(root, text="Update IVI (Celsius → Fahrenheit)", font=("Arial", 14),
                        command=lambda: send_update_trigger(DID_IVI_UPDATE, 1))
    ivi_btn.pack(pady=10)

    def tcu_update_action():
        send_update_trigger(DID_TCU_UPDATE, 1)
        status_label.config(text="TCU update triggered!")

    tcu_btn = tk.Button(root, text="Update TCU (Show Message)", font=("Arial", 14),
                        command=tcu_update_action)
    tcu_btn.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()