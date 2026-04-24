import random
from udpWithRdt import connection
def run_client():
    client_port = random.randint(10000,60000) # choose a random port for the client destination port is 8080 for the server
    client_conn = connection(srcPort=client_port, destPort=8080, destIP="127.0.0.1",seqNo=0,ackNo=0) # create a connection object for the client
    print(f"[Client] Starting on {client_port} and connecting to server on port 8080...")
    client_conn.connect() # perform 3-way handshake to establish connection with the server
    print("[Client] Connection established with server.")
    http_request = "GET /index.html HTTP/1.0\r\n" \
                   "Host: 127.0.0.1\r\n" \
                   "User-Agent: Custom-RDT-Client\r\n" \
                   "Connection: close\r\n\r\n"
    print(f"[Client] Sending HTTP request:\n{http_request}")
    client_conn.send(http_request,loss=0,corrupt=0) # send the HTTP request to the server
    print("[Client] Request sent. Waiting for response...")
    response_bytes = client_conn.recevAll() # receive the response from the server
    if response_bytes:
        print(f"\n--- Server Response ---\n{response_bytes.decode('utf-8')}\n-----------------------")
    else:
        print("[Client] No response received.")
        
    # 5. Close the connection
    print("\n[Client] Closing connection...")
    client_conn.close()

if __name__ == "__main__":
    run_client()
    