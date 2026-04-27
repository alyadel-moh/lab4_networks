import time
import threading
import socket
import random
import inspect
from udpWithRdt import connection, packet, SYN, ACK, SYNACK, FIN, END

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
SEP  = "=" * 55

results = []

def log(name, passed, note=""):
    status = PASS if passed else FAIL
    print(f"{status} {name}" + (f" — {note}" if note else ""))
    results.append((name, passed))


# ── Background Server using YOUR Protocol ─────────────────
def run_test_server():
    # Using port 8085 for testing to avoid conflict if your main server is running
    server_conn = connection(srcPort=8085, destPort=0, destIP="", seqNo=0, ackNo=0)
    
    while True:
        try:
            server_conn.accept()
            req_bytes = server_conn.recevAll()
            if not req_bytes:
                continue
                
            msg = req_bytes.decode('utf-8')
            
            # Build responses based on request
            if msg.startswith("GET"):
                if msg.startswith("GET /index"):
                    body = "<html><body><h1>Hello World</h1></body></html>"
                    response = f"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n{body}"
                else:
                    body = "Page not found"
                    response = f"HTTP/1.0 404 NOT FOUND\r\nContent-Type: text/plain\r\nContent-Length: {len(body)}\r\n\r\n{body}"
            elif msg.startswith("POST"):
                if msg.startswith("POST /index"):
                    body = "POST received: Hello"
                    response = f"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(body)}\r\n\r\n{body}"
                else:
                    body = "Page not found"
                    response = f"HTTP/1.0 404 NOT FOUND\r\nContent-Type: text/plain\r\nContent-Length: {len(body)}\r\n\r\n{body}"
            else:
                body = "Invalid request"
                response = f"HTTP/1.0 400 BAD REQUEST\r\nContent-Type: text/plain\r\nContent-Length: {len(body)}\r\n\r\n{body}"

            # Send response and cleanly close
            server_conn.send(response)
            server_conn.waitClose()
            
            # Reset connection state for next test client
            server_conn.seqNo = 0
            server_conn.ackNo = 0
            
        except Exception:
            pass

def start_server():
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    time.sleep(0.5)

# Client helper using YOUR connection class
def make_client():
    client_port = random.randint(10000, 60000)
    c = connection(srcPort=client_port, destPort=8085, destIP="127.0.0.1", seqNo=0, ackNo=0)
    try:
        c.connect()
        return c
    except Exception:
        return None


# ── Test Cases ────────────────────────────────────────────

def test1_get_index():
    c = make_client()
    if not c:
        log("TC1  Normal GET /index", False, "could not connect"); return
    c.send("GET /index HTTP/1.0\r\n\r\n")
    r = c.recevAll().decode('utf-8')
    c.close()
    passed = "200 OK" in r and "Hello World" in r
    log("TC1  Normal GET /index", passed, r.splitlines()[0] if r else "No response")


def test2_get_wrong():
    c = make_client()
    if not c:
        log("TC2  Invalid GET /wrong", False, "could not connect"); return
    c.send("GET /wrong HTTP/1.0\r\n\r\n")
    r = c.recevAll().decode('utf-8')
    c.close()
    passed = "404 NOT FOUND" in r and "Page not found" in r
    log("TC2  Invalid GET /wrong", passed, r.splitlines()[0] if r else "No response")


def test3_post_index():
    c = make_client()
    if not c:
        log("TC3  POST /index", False, "could not connect"); return
    c.send("POST /index HTTP/1.0\r\n\r\nHello")
    r = c.recevAll().decode('utf-8')
    c.close()
    passed = "200 OK" in r and "POST received: Hello" in r
    log("TC3  POST /index", passed, r.splitlines()[0] if r else "No response")


def test4_bad_method():
    c = make_client()
    if not c:
        log("TC4  Bad method → 400", False, "could not connect"); return
    c.send("DELETE /index HTTP/1.0\r\n\r\n")
    r = c.recevAll().decode('utf-8')
    c.close()
    passed = "400 BAD REQUEST" in r
    log("TC4  Bad method → 400", passed, r.splitlines()[0] if r else "No response")


def test5_post_wrong_path():
    c = make_client()
    if not c:
        log("TC5  POST wrong path → 404", False, "could not connect"); return
    c.send("POST /wrong data HTTP/1.0\r\n\r\n")
    r = c.recevAll().decode('utf-8')
    c.close()
    passed = "404 NOT FOUND" in r
    log("TC5  POST wrong path → 404", passed, r.splitlines()[0] if r else "No response")


def test6_checksum():
    pkt = packet(seqNo=1, ackNo=0, flags=SYN, checksum=0, data=b"Hello Checksum")
    pkt.calcChecksum()
    is_clean_valid = pkt.verifyChecksum()
    
    pkt.simulateCorruption(1.0) # 100% corruption chance
    is_corrupted_valid = pkt.verifyChecksum()
    
    passed = is_clean_valid and not is_corrupted_valid
    log("TC6  Checksum detection", passed,
        "corrupt detected ✓, clean passed ✓" if passed else "checksum logic wrong")


def test7_packet_roundtrip():
    original_data = b"GET /index"
    pkt = packet(seqNo=5, ackNo=10, flags=END, checksum=0, data=original_data)
    pkt.calcChecksum()
    
    raw_bytes = pkt.toBytes()
    rebuilt = packet.unpackBytesToPkt(raw_bytes)
    
    passed = rebuilt.seqNo == 5 and rebuilt.flags == END and rebuilt.data == original_data
    log("TC7  Packet round-trip", passed, f"seq={rebuilt.seqNo} flag={rebuilt.flags} data='{rebuilt.data}'")


def test8_sequence_numbers():
    c = make_client()
    if not c:
        log("TC8  Sequence increments", False, "could not connect"); return
    seq_before = c.seqNo
    c.send("GET /index HTTP/1.0\r\n\r\n")
    c.recevAll()
    seq_after = c.seqNo
    c.close()
    passed = seq_before != seq_after
    log("TC8  Sequence increments", passed, f"seq moved from {seq_before} to {seq_after}")


def test9_loss_simulation():
    # Checks if your simulateLoss and simulateCorruption methods exist
    passed = hasattr(packet, "simulateLoss") and hasattr(packet, "simulateCorruption")
    log("TC9  Loss simulation code exists", passed)


def test10_fin():
    c = make_client()
    if not c:
        log("TC10 FIN termination", False, "could not connect"); return
    c.send("GET /index HTTP/1.0\r\n\r\n")
    c.recevAll()
    try:
        c.close() # Should send FIN gracefully
        passed = True
    except Exception:
        passed = False
    log("TC10 FIN termination", passed)


def test11_http_headers():
    c = make_client()
    if not c:
        log("TC11 HTTP headers present", False, "could not connect"); return
    c.send("GET /index HTTP/1.0\r\n\r\n")
    r = c.recevAll().decode('utf-8')
    c.close()
    has_ct = "Content-Type" in r
    has_cl = "Content-Length" in r
    passed = has_ct and has_cl
    log("TC11 HTTP headers present", passed,
        f"Content-Type={'✓' if has_ct else '✗'}  Content-Length={'✓' if has_cl else '✗'}")


def test12_multiple_clients():
    local = []
    for _ in range(2):
        c = make_client()
        if not c:
            local.append(False); continue
        c.send("GET /index HTTP/1.0\r\n\r\n")
        r = c.recevAll().decode('utf-8')
        c.close()
        local.append("200 OK" in r)
        time.sleep(0.3)
    passed = all(local)
    log("TC12 Multiple sequential clients", passed, f"results: {local}")


# ── Main ──────────────────────────────────────────────────

if __name__ == "__main__":
    print(SEP)
    print("  CC451 Lab 4 — Automated Test Cases Runner")
    print(SEP)
    print("\n[*] Starting your custom server in background...\n")
    start_server()

    tests = [
        test1_get_index, test2_get_wrong, test3_post_index,
        test4_bad_method, test5_post_wrong_path, test6_checksum,
        test7_packet_roundtrip, test8_sequence_numbers, test9_loss_simulation,
        test10_fin, test11_http_headers, test12_multiple_clients,
    ]

    print()
    for test in tests:
        try:
            # We wrap the test execution to avoid printing debug logs from your connection code
            import sys, os
            old_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')  # add encoding='utf-8'
            try:
                test()
            finally:
                sys.stdout.close()
                sys.stdout = old_stdout
                
        except Exception as e:
            sys.stdout = old_stdout
            log(test.__name__, False, f"exception: {e}")
        time.sleep(0.5)

    total  = len(results)
    passed = sum(1 for _, p in results if p)
    print()
    print(SEP)
    print(f"  Results: {passed}/{total} passed")
    print(SEP)