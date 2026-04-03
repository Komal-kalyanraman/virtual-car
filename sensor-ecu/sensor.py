import random
import socket
import struct
import threading
import time

DID_VEHICLE_SPEED = 0xF190
DID_CABIN_TEMP = 0xF191

DOIP_VERSION = 0x02
DOIP_INVERSE_VERSION = 0xFD
DOIP_PAYLOAD_DIAG_MSG = 0x8001

SENSOR_LOGICAL_ADDR = 0x0A00

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
		raise ValueError(f"Unsupported payload type 0x{payload_type:04X}")

	payload = recv_exact(sock, payload_len)
	if len(payload) < 4:
		raise ValueError("Diagnostic payload too short")

	source_addr, target_addr = struct.unpack("!HH", payload[:4])
	uds_payload = payload[4:]
	return source_addr, target_addr, uds_payload


def handle_uds(uds_request):
	if not uds_request:
		return bytes([0x7F, 0x00, 0x13])

	sid = uds_request[0]
	if sid != 0x22 or len(uds_request) < 3:
		return bytes([0x7F, sid, 0x11])

	did = (uds_request[1] << 8) | uds_request[2]
	if did == DID_VEHICLE_SPEED:
		value = vehicle_speed
		return bytes([0x62, uds_request[1], uds_request[2]]) + value.to_bytes(2, "big")
	if did == DID_CABIN_TEMP:
		value = cabin_temp
		return bytes([0x62, uds_request[1], uds_request[2]]) + value.to_bytes(2, "big")
	return bytes([0x7F, sid, 0x31])


def handle_client(conn, peer):
	print(f"DoIP client connected: {peer}")
	with conn:
		conn.settimeout(5.0)
		try:
			while True:
				source_addr, target_addr, uds_request = recv_doip_diag(conn)
				if target_addr != SENSOR_LOGICAL_ADDR:
					uds_response = bytes([0x7F, uds_request[0] if uds_request else 0x00, 0x31])
				else:
					uds_response = handle_uds(uds_request)

				response_frame = build_doip_diag_frame(
					SENSOR_LOGICAL_ADDR,
					source_addr,
					uds_response,
				)
				print(
					f"RX DoIP UDS={uds_request.hex()} -> TX UDS={uds_response.hex()}"
				)
				conn.sendall(response_frame)
		except (ConnectionError, socket.timeout):
			print(f"DoIP client disconnected: {peer}")
		except Exception as exc:
			print(f"DoIP client error {peer}: {exc}")


def main():
	threading.Thread(target=update_vehicle_speed, daemon=True).start()
	threading.Thread(target=update_cabin_temp, daemon=True).start()

	host = "0.0.0.0"
	port = 13400
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server.bind((host, port))
		server.listen(5)
		print(f"Sensor ECU DoIP server listening on {host}:{port}")

		while True:
			conn, peer = server.accept()
			threading.Thread(target=handle_client, args=(conn, peer), daemon=True).start()


if __name__ == "__main__":
	main()
