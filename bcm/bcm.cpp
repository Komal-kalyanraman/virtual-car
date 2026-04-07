#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <filesystem>
#include <cstring>
#include <linux/can.h>
#include <linux/can/isotp.h>
#include <sys/socket.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>

constexpr uint16_t DID_VEHICLE_SPEED = 0xF190;
const std::string DATA_DIR = "./data";
const std::string FLAG_PATH = DATA_DIR + "/bcm_update.flag";

// Helper to open an ISO-TP socket
int open_isotp_socket(const char* ifname, uint16_t txid, uint16_t rxid) {
    int s = socket(PF_CAN, SOCK_DGRAM, CAN_ISOTP);
    if (s < 0) {
        perror("socket");
        return -1;
    }
    struct sockaddr_can addr = {};
    addr.can_family = AF_CAN;
    addr.can_addr.tp.tx_id = txid;
    addr.can_addr.tp.rx_id = rxid;
    struct ifreq ifr;
    std::strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    ioctl(s, SIOCGIFINDEX, &ifr);
    addr.can_ifindex = ifr.ifr_ifindex;
    if (bind(s, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(s);
        return -1;
    }
    return s;
}

// Helper to send a UDS ReadDataByIdentifier request and receive response
bool uds_read_data_by_identifier(int sock, uint16_t did, uint16_t& value) {
    // UDS ReadDataByIdentifier: 0x22, then DID (big endian)
    uint8_t req[3] = {0x22, static_cast<uint8_t>(did >> 8), static_cast<uint8_t>(did & 0xFF)};
    if (write(sock, req, 3) != 3) return false;
    uint8_t resp[16];
    int n = read(sock, resp, sizeof(resp));
    if (n < 5) return false;
    // Response: 0x62, DID_H, DID_L, DATA_H, DATA_L
    if (resp[0] == 0x62 && resp[1] == req[1] && resp[2] == req[2]) {
        value = (resp[3] << 8) | resp[4];
        return true;
    }
    return false;
}

int main() {
    std::filesystem::remove(FLAG_PATH);

    int sock = open_isotp_socket("vcan0", 0x7E0, 0x7E8);
    if (sock < 0) {
        std::cerr << "Failed to open ISO-TP socket" << std::endl;
        return 1;
    }

    double sleep_time = 0.1;
    while (true) {
        try {
            if (std::filesystem::exists(FLAG_PATH)) {
                sleep_time = 1.0;
                std::cout << "BCM: Data rate changed to 1000ms due to TCU update trigger." << std::endl;
            }
            uint16_t speed = 0;
            if (uds_read_data_by_identifier(sock, DID_VEHICLE_SPEED, speed)) {
                std::cout << "Vehicle Speed: " << speed << " km/h" << std::endl;
            } else {
                std::cerr << "Error reading vehicle speed" << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "Exception: " << e.what() << std::endl;
        }
        std::this_thread::sleep_for(std::chrono::duration<double>(sleep_time));
    }
    close(sock);
    return 0;
}