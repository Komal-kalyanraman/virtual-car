import os
import time
import isotp

from udsoncan.client import Client
from udsoncan.connections import IsoTPConnection
from udsoncan import configs
from udsoncan.common.DidCodec import DidCodec

DID_VEHICLE_SPEED = 0xF190

class UInt16DidCodec(DidCodec):
    def encode(self, val):
        return int(val).to_bytes(2, byteorder="big", signed=False)
    def decode(self, payload):
        return int.from_bytes(payload, byteorder="big", signed=False)
    def __len__(self):
        return 2

def main():
    address = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x7E0,
        rxid=0x7E8,
    )
    conn = IsoTPConnection("vcan0", address=address, params={"use_socketcan": True})
    client_config = dict(configs.default_client_config)
    client_config["data_identifiers"] = {
        DID_VEHICLE_SPEED: UInt16DidCodec(),
    }
    with Client(conn, request_timeout=2, config=client_config) as client:
        sleep_time = 0.1
        while True:
            try:
                if os.path.exists("/tmp/bcm_update.flag"):
                    sleep_time = 1.0
                    os.remove("/tmp/bcm_update.flag")
                    print("BCM: Data rate changed to 1000ms due to TCU update trigger.")
                response = client.read_data_by_identifier(DID_VEHICLE_SPEED)
                speed = response.service_data.values[DID_VEHICLE_SPEED]
                print(f"Vehicle Speed: {speed} km/h")
            except Exception as e:
                print("Error reading vehicle speed:", e)
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()