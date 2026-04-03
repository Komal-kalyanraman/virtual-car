import time
import isotp
import threading
import tkinter as tk

from udsoncan.client import Client
from udsoncan.connections import IsoTPConnection
from udsoncan import configs
from udsoncan.common.DidCodec import DidCodec

DID_CABIN_TEMP = 0xF191

class UInt16DidCodec(DidCodec):
    def encode(self, val):
        return int(val).to_bytes(2, byteorder="big", signed=False)
    def decode(self, payload):
        return int.from_bytes(payload, byteorder="big", signed=False)
    def __len__(self):
        return 2

class Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Vehicle Dashboard - Cabin Temperature")
        self.label = tk.Label(root, text="Cabin Temperature: -- °C", font=("Arial", 32))
        self.label.pack(padx=40, pady=40)
        self.temp = "--"

    def update_temp(self, temp):
        self.temp = temp
        self.label.config(text=f"Cabin Temperature: {temp} °C")

def uds_temp_reader(dashboard):
    address = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x7E0,
        rxid=0x7E8,
    )
    conn = IsoTPConnection("vcan0", address=address, params={"use_socketcan": True})
    client_config = dict(configs.default_client_config)
    client_config["data_identifiers"] = {
        DID_CABIN_TEMP: UInt16DidCodec(),
    }
    with Client(conn, request_timeout=2, config=client_config) as client:
        while True:
            try:
                response = client.read_data_by_identifier(DID_CABIN_TEMP)
                temp = response.service_data.values[DID_CABIN_TEMP]
                dashboard.root.after(0, dashboard.update_temp, temp)
            except Exception as e:
                dashboard.root.after(0, dashboard.update_temp, "--")
            time.sleep(3)

def main():
    root = tk.Tk()
    dashboard = Dashboard(root)
    threading.Thread(target=uds_temp_reader, args=(dashboard,), daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()