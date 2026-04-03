import udsoncan
from udsoncan.connections import ISOTPConnection
from udsoncan.services import ReadDataByIdentifier
import time

DID_VEHICLE_SPEED = 0xF190

def main():
    conn = ISOTPConnection('vcan0', rxid=0x7E8, txid=0x7E0, params={'use_socketcan': True})
    with udsoncan.client.Client(conn, request_timeout=2) as client:
        while True:
            response = client.read_data_by_identifier(DID_VEHICLE_SPEED)
            speed = int.from_bytes(response.service_data.values[DID_VEHICLE_SPEED], 'big')
            print(f"Vehicle Speed: {speed} km/h")
            time.sleep(0.1)

if __name__ == "__main__":
    main()