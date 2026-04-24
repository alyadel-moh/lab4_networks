import socket
import random
from udpWithRdt import connection

def run_proxy():
    # 1. Setup a standard TCP socket to listen to the web browser
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('127.0.0.1', 8081)) # Proxy listens on port 8081
    tcp_socket.listen(1)
    
    print("[Proxy] Listening for Web Browser on http://127.0.0.1:8081")
    
    while True:
        # 2. Accept connection from the web browser
        browser_conn, addr = tcp_socket.accept()
        browser_request = browser_conn.recv(1024)
        
        if not browser_request:
            browser_conn.close()
            continue
            
        print("\n[Proxy] Received request from Browser. Forwarding via Custom UDP RDT...")
        
        # 3. Create your custom RDT Client connection
        rdt_port = random.randint(10000, 60000)
        rdt_client = connection(srcPort=rdt_port, destPort=8080, destIP="127.0.0.1", seqNo=0, ackNo=0)
        
        try:
            # 4. Do your UDP 3-way handshake
            rdt_client.connect()
            
            # 5. Send the browser's raw TCP request over your UDP protocol
            rdt_client.send(browser_request, loss=0.0, corrupt=0.0)
            
            # 6. Receive the HTML response from your server
            server_response = rdt_client.recevAll()
            
            # 7. Send the response back to the web browser via TCP
            if server_response:
                browser_conn.sendall(server_response)
                
            rdt_client.close()
            
        except Exception as e:
            print(f"[Proxy] Error: {e}")
            
        finally:
            browser_conn.close()
            print("[Proxy] Finished serving browser request.")

if __name__ == "__main__":
    run_proxy()