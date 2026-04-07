#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <errno.h>
#include <time.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <limits.h>
#include <libgen.h>

#define DOIP_VERSION 0x02
#define DOIP_INVERSE_VERSION 0xFD
#define DOIP_PAYLOAD_DIAG_MSG 0x8001

#define IVI_LOGICAL_ADDR 0x0B00
#define GW_LOGICAL_ADDR  0x0E00

#define DID_CABIN_TEMP 0xF191

#define GATEWAY_HOST "127.0.0.1"
#define GATEWAY_PORT 15000

// Helper to read exactly n bytes from a socket
int recv_exact(int sock, void *buf, size_t size) {
    size_t received = 0;
    while (received < size) {
        ssize_t r = recv(sock, (char*)buf + received, size - received, 0);
        if (r <= 0) return -1;
        received += r;
    }
    return 0;
}

// Build DoIP diagnostic frame
size_t build_doip_diag_frame(uint16_t source_addr, uint16_t target_addr, const uint8_t *uds_payload, size_t uds_len, uint8_t *out) {
    // Header: version, inverse, payload type, length
    out[0] = DOIP_VERSION;
    out[1] = DOIP_INVERSE_VERSION;
    out[2] = (DOIP_PAYLOAD_DIAG_MSG >> 8) & 0xFF;
    out[3] = DOIP_PAYLOAD_DIAG_MSG & 0xFF;
    uint32_t plen = 4 + uds_len;
    out[4] = (plen >> 24) & 0xFF;
    out[5] = (plen >> 16) & 0xFF;
    out[6] = (plen >> 8) & 0xFF;
    out[7] = plen & 0xFF;
    // Payload: source, target, uds
    out[8] = (source_addr >> 8) & 0xFF;
    out[9] = source_addr & 0xFF;
    out[10] = (target_addr >> 8) & 0xFF;
    out[11] = target_addr & 0xFF;
    memcpy(out + 12, uds_payload, uds_len);
    return 12 + uds_len;
}

// Check if the update flag file exists
int check_update_flag(const char *flag_path) {
    struct stat st;
    return stat(flag_path, &st) == 0;
}

int main() {
    int show_fahrenheit = 0;
    char flag_path[PATH_MAX];
    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len < 0) {
        perror("readlink");
        return 1;
    }
    exe_path[len] = '\0';
    char *exe_dir = dirname(exe_path);
    snprintf(flag_path, sizeof(flag_path), "%s/data/ivi_update.flag", exe_dir);

    /* Remove previous IVI update flag file at startup */
    if (check_update_flag(flag_path)) {
        unlink(flag_path);
    }

    while (1) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            perror("socket");
            sleep(1);
            continue;
        }

        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(GATEWAY_PORT);
        inet_pton(AF_INET, GATEWAY_HOST, &addr.sin_addr);

        if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            perror("connect");
            close(sock);
            sleep(1);
            continue;
        }

        printf("Connected to gateway DoIP %s:%d\n", GATEWAY_HOST, GATEWAY_PORT);

        while (1) {
            // Check for update trigger
            if (check_update_flag(flag_path)) {
                show_fahrenheit = 1;
                printf("IVI: Switched to Fahrenheit display due to TCU update trigger.\n");
            }

            // Build UDS ReadDataByIdentifier request
            uint8_t uds_req[3] = {0x22, 0xF1, 0x91};
            uint8_t frame[32];
            size_t frame_len = build_doip_diag_frame(IVI_LOGICAL_ADDR, GW_LOGICAL_ADDR, uds_req, 3, frame);

            if (send(sock, frame, frame_len, 0) != (ssize_t)frame_len) {
                perror("send");
                break;
            }

            // Receive DoIP response header
            uint8_t header[8];
            if (recv_exact(sock, header, 8) < 0) {
                perror("recv header");
                break;
            }
            if (header[0] != DOIP_VERSION || header[1] != DOIP_INVERSE_VERSION) {
                fprintf(stderr, "Invalid DoIP version\n");
                break;
            }
            uint16_t payload_type = (header[2] << 8) | header[3];
            if (payload_type != DOIP_PAYLOAD_DIAG_MSG) {
                fprintf(stderr, "Unsupported payload type: 0x%04X\n", payload_type);
                break;
            }
            uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
            if (payload_len < 4 || payload_len > 32) {
                fprintf(stderr, "Payload length error\n");
                break;
            }

            uint8_t payload[32];
            if (recv_exact(sock, payload, payload_len) < 0) {
                perror("recv payload");
                break;
            }

            uint16_t src = (payload[0] << 8) | payload[1];
            uint16_t dst = (payload[2] << 8) | payload[3];
            uint8_t *uds_resp = payload + 4;
            size_t uds_len = payload_len - 4;

            int ok = (src == GW_LOGICAL_ADDR) && (dst == IVI_LOGICAL_ADDR) &&
                     (uds_len >= 5) && (uds_resp[0] == 0x62) &&
                     (uds_resp[1] == 0xF1) && (uds_resp[2] == 0x91);

            if (ok) {
                int temp = (uds_resp[3] << 8) | uds_resp[4];
                if (show_fahrenheit) {
                    int temp_f = (int)((temp * 9.0 / 5.0) + 32.0 + 0.5);
                    printf("Cabin Temperature: %d F\n", temp_f);
                } else {
                    printf("Cabin Temperature: %d C\n", temp);
                }
            } else {
                printf("Cabin Temperature: --\n");
            }

            sleep(3);
        }

        close(sock);
        printf("IVI DoIP error: reconnecting...\n");
        sleep(1);
    }
    return 0;
}