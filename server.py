from udpWithRdt import connection
def run_server():
    print("Server is running...")
    server_conn = connection(srcPort=8080,destPort=0,destIP="",seqNo=0,ackNo=0) #create a connection object for the server
    print("[Server] Listening on port 8080...")
    while True:
        try:
            server_conn.accept() # accept 3-way handshake
            req_bytes = server_conn.recevAll() # receive the request from the client
            if not req_bytes:
                print("[Server] No data received. Closing connection.")
                server_conn.close()
                continue
            request_str = req_bytes.decode('utf-8') # decode the request bytes to string
            print(f"\n--- Received Request ---\n{request_str}\n-------------------")
            lines = request_str.split('\r\n') # split the request into lines
            request_line = lines[0].split(' ') # the first line is the request line
            if len(request_line) >=2:
                method, path = request_line[0], request_line[1] # get the method and path from the request line
                if method == 'GET': # if the method is GET, handle the request
                    if path == "/" or path == "/index.html":
                        # 200 OK Response
                        body = "<html><body><h1>hello from Reliable UDP Server!</h1></body></html>"
                        response = f"HTTP/1.0 200 OK\r\n" \
                                    f"Content-Type: text/html\r\n" \
                                    f"Content-Length: {len(body)}\r\n" \
                                    f"Connection: close\r\n\r\n" \
                                    f"{body}"
                    else:
                        # 404 Not Found Response
                        body = "<html><body><h1>File Not Found</h1></body></html>"
                        response = f"HTTP/1.0 404 Not Found\r\n" \
                                    f"Content-Type: text/html\r\n" \
                                    f"Content-Length: {len(body)}\r\n" \
                                    f"Connection: close\r\n\r\n" \
                                    f"{body}"
                elif method == 'POST': # if the method is POST, handle the request
                    body = "<html><body><h1>POST request received!</h1></body></html>"
                    response = f"HTTP/1.0 200 OK\r\n" \
                                f"Content-Type: text/html\r\n" \
                                f"Content-Length: {len(body)}\r\n" \
                                f"Connection: close\r\n\r\n" \
                                f"{body}"
                else:
                # Method not supported
                    response = "HTTP/1.0 405 Method Not Allowed\r\n\r\n"
                server_conn.send(response)
            server_conn.waitClose() # wait for the client to close the connection
            print("[Server] Connection closed. Listening for next client...\n")
            # Reset connection state for the next client
            server_conn.seqNo = 0
            server_conn.ackNo = 0
        except KeyboardInterrupt:
            print("\n[Server] Shutting down.")
            break

if __name__ == "__main__":
    run_server()

