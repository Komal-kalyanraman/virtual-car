import time
import isotp

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


def main():
    # Client sends on 0x7E0 and receives on 0x7E8
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
            response = client.read_data_by_identifier(DID_CABIN_TEMP)
            temp = response.service_data.values[DID_CABIN_TEMP]
            print(f"Cabin Temperature: {temp} C")
            time.sleep(3)


if __name__ == "__main__":
    main()