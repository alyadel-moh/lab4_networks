import struct
import random
import socket

# flags for 3 way handshake since the flags is set to be a byte in size syn = 0b0000 0001, ack= 0b0000 0010, synack=0b0000 0011 (syn|ack) , fin= 0b0000 0100
SYN = 1
ACK = 2
FIN = 4
SYNACK = SYN | ACK  # = 3
HDR_LEN = 7   
CHUNK_SIZE = 512 # max data size in each packet 
END = 8 # last chunk of message
# class that represents a packet everytime we want to send a packet we will make a new instance of the class and send it over the network


# 1. Packet structure
class packet:
    def __init__(self, seqNo, ackNo, flags, checksum, data):
        self.seqNo = seqNo
        self.ackNo = ackNo
        self.flags = flags
        self.checksum = checksum
        self.data = data

    # converts the packet to bytes to send over UDP connection
    def toBytes(self):
        # if the data is already bytes keep it as it is
        data = self.data
        # otherwise encode to bytes
        if isinstance(self.data, str):
            data = self.data.encode()
        return struct.pack(
            f"=HHBH{len(data)}s",
            self.seqNo,
            self.ackNo,
            self.flags,
            self.checksum,
            data,
        )
    
    
    # converts raw bytes to a packet object, used at the receiver to convert the received bytes into a packet object to read the fields and verify checksum
    @staticmethod
    def fromBytes(raw):
        if len(raw) < HDR_LEN:
            raise ValueError("Packet too short {len(raw)} to be valid bytes")
        seqNo, ackNo, flags, checksum, data = struct.unpack(
            f"=HHBH{len(raw)-HDR_LEN}s", raw
        )
        return packet(seqNo, ackNo, flags, checksum, data)
    
    # converts raw_bytes to a packet
    # header length = 2(seq#) + 2(ack#) + 1(flags) + 2(checksum) = 7 bytes in total
    @staticmethod
    def unpackBytesToPkt(raw_bytes):
        seqNo, ackNo, flags, checksum, data = struct.unpack(
            f"=HHBH{len(raw_bytes)-HDR_LEN}s", raw_bytes
        )
        return packet(seqNo, ackNo, flags, checksum, data)

    # 2. Checksum
    def calcChecksum(self):
        # Used at sender to calcChecksum to be checked at the reciever
        # we first start of with the checksum = 0 at sender so it wont affect the overall sum
        self.checksum = 0
        # turns the packet to bytes
        raw_bytes = self.toBytes()
        # if length is odd pad with zeros (even # of bytes so we can divide them into pairs of 16 bit fields to add them in checksum)
        if len(raw_bytes) % 2 == 1:
            raw_bytes += b"\x00"
        # summing all bytes including headers
        total = 0
        for i in range(0, len(raw_bytes), 2):
            word = (raw_bytes[i] << 8) + raw_bytes[i + 1]
            total += word
            # if there is a carry after adding this pair wrap around
            total = (total & 0xFFFF) + (total >> 16)
        # 1's complement
        self.checksum = ~total & 0xFFFF

    def verifyChecksum(self):
        raw_bytes = self.toBytes()
        if len(raw_bytes) % 2 == 1:
            raw_bytes += b"\x00"

        total = 0
        for i in range(0, len(raw_bytes), 2):
            word = (raw_bytes[i] << 8) + raw_bytes[i + 1]
            total += word
            total = (total & 0xFFFF) + (total >> 16)
        # returns true if the sum+checksum is all ones (which is the sum of the whole packet)
        return total == 0xFFFF

    # 3. 4.Simulate packet loss/corruption
    # whether to drop the packet or not
    def simulateLoss(self, probability):
        return random.random() < probability

    # corrupt the checksum by adding 1
    def simulateCorruption(self, probability):
        if random.random() < probability:
            # to stay 16 bits we and with 1's
            self.checksum = (self.checksum + 1) & 0xFFFF


class connection:
    def __init__(self, srcPort, destPort, destIP, seqNo, ackNo):
        self.srcPort = srcPort
        self.destPort = destPort
        self.destIP = destIP 
        self.seqNo = seqNo
        self.ackNo = ackNo
        # create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # bind to source port on all interfaces
        self.socket.bind(("", self.srcPort))
        # to store address to send to after connection is established   
        self.peerAddr = None  
      # makes recvfrom() raise a socket.timeout exception if no data arrives in time.
        self.socket.settimeout(2)

    def connect(self):
        # called by client to intiate connection
        # 1. Create SYN packet
        # not that the control packets contain no data that is why data=b""
        synPkt = packet(seqNo=0, ackNo=0, flags=SYN, checksum=0, data=b"")
        # 2. caclulate checksum
        synPkt.calcChecksum()
        # 3.send packet
        self._sendTo(synPkt)  
        # 4. wait for synack note 2.1
        raw_bytes, addr = self._recvFrom()    
        # 5. convert raw_bytes to packets
        synAckPkt = packet.unpackBytesToPkt(raw_bytes)
        # 6. wait for SYNACK to send ACK
        if synAckPkt.verifyChecksum() and synAckPkt.flags == SYNACK:
            self.peerAddr = addr
            # synAck
            # synNo = 1 syn consumes 1 sequence # by convention
            ackPkt = packet(
                seqNo=1,
                ackNo=(synAckPkt.seqNo + 1) & 0xFFFF,
                flags=ACK,
                checksum=0,
                data=b"",
            )
            ackPkt.calcChecksum()
            self._sendTo(ackPkt) 
            self.seqNo = 1
            self.ackNo = 1

    def accept(self):
        # server side
        # 1. wait for SYN
        raw_bytes, addr = self._recvFrom()  
        # store the client's address to send to after connection is established
        self.peerAddr = addr
        # 2. unpack raw bytes to packet
        rcvedPkt = packet.unpackBytesToPkt(raw_bytes)
        # 3. check if it is a SYN
        if rcvedPkt.verifyChecksum() and rcvedPkt.flags == SYN:
            # 4. send SYNACK
            synAckPkt = packet(
                seqNo=0,
                ackNo=(rcvedPkt.seqNo + 1) & 0xFFFF,
                flags=SYNACK,
                checksum=0,
                data=b"",
            )
            synAckPkt.calcChecksum()
            self._sendTo(synAckPkt)  
            # 5. wait for ACK
            raw_bytes, addr = self._recvFrom()  
            rcvedPkt = packet.unpackBytesToPkt(raw_bytes)
            # 6. check if it is an ACK
            if rcvedPkt.verifyChecksum() and rcvedPkt.flags == ACK:
                # connection established
                self.seqNo = 1
                self.ackNo = 1
                print("[server] connection established!")

    def send(self, data, loss=0.0, corrupt=0.0):
        if isinstance(data, str):
            data = data.encode() # if the data is a string encode it to bytes, if it's already bytes keep it as it is, if it's None set it to empty bytes
        if not data:
            data = b""  # if data is None or empty string set it to empty bytes
        chunks = [data[i:i+CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)] # split the data into chunks of size CHUNK_SIZE (512 bytes) to fit in one packet
        for i, chunk in enumerate(chunks):
            flags = END if i == len(chunks) - 1 else 0 # set the END flag for the last chunk
            self._sendChunk(chunk, flags, loss, corrupt) # send each chunk with the appropriate flags
    def _sendChunk(self,chunk, flags, loss, corrupt):
        pkt = packet(self.seqNo, 0, flags, 0,chunk)
          # 2. calculate checksum
        pkt.calcChecksum()
        saved_checksum = pkt.checksum  # save the original checksum to restore it after simulating corruption
        while True:
            # 4. simulate loss/corruption
            lost = pkt.simulateLoss(loss)
            pkt.simulateCorruption(corrupt)
            # 5. send if not lost
            if not lost:
                self._sendTo(pkt) 
            try:
                # 6. wait for ACK after sending (or not if lost)
                # receive is a blocking call but if timeout it will go to except and interrupt
                ack_pkt, _ = self._recvFrom() 
                expected_ackNo = (self.seqNo + len(chunk)) & 0xFFFF 
                if (
                    ack_pkt.verifyChecksum()
                    and ack_pkt.flags == ACK
                    # expected ack
                    and ack_pkt.ackNo == expected_ackNo
                ):
                    # forces wrap around
                    self.seqNo = expected_ackNo
                    return
            except socket.timeout:
                pass  # timeout will cause us to resend the packet
            print("[sender] timeout, resending packet with seqNo", self.seqNo)
            pkt.checksum = saved_checksum  # restore the original checksum before resending
    def recv(self):
        while True:
            try:
                pkt , addr = self._recvFrom()
            except socket.timeout: # if timeout occurs, we just go back to waiting for the packet again, this is how we handle duplicates and lost packets at the receiver
                return None,False
            if pkt is None:
                return None,False
            self.peerAddr = addr
            if not pkt.verifyChecksum():
                print("[receiver] packet with seqNo", pkt.seqNo, "failed checksum, discarding")
                continue
            if pkt.seqNo != self.ackNo:
                print("[receiver] packet with seqNo", pkt.seqNo, "is a duplicate, discarding")
                ack = packet(self.seqNo,self.ackNo,ACK, 0, b"")
                ack.calcChecksum()
                self.socket.sendto(ack.toBytes(),addr) # resend the ack for the last in order packet to help the sender recover from lost acks
                continue
            # if we reach here it means the packet is not lost, not corrupted and not a duplicate, so we can send an ack for it and return the data
            new_ack = (pkt.seqNo + len(pkt.data)) & 0xFFFF
            ack = packet(self.seqNo,new_ack , ACK, 0, b"")
            ack.calcChecksum()
            self.socket.sendto(ack.toBytes(),addr)
            self.ackNo = new_ack
            return pkt.data,bool(pkt.flags & END) # return the data and whether this is the last chunk of the message (END flag is set)
        
    def recevAll(self):
        buf = b""
        while True:
            chunk,is_end = self.recv() # recv returns the data and whether this is the last chunk of the message (END flag is set)
            if chunk is None:
                break # if recv returns None it means we had a timeout waiting for the packet, we can just break and return whatever we have in the buffer so far, this is how we handle lost packets at the receiver
            buf += chunk # append the chunk to the buffer
            if is_end:  # if this is the last chunk of the message, we can stop receiving and return the full message
                break
        return buf 

    def close(self):
        # called by client to initiate closing (sending fin and wait for ack)
        finPkt = packet(seqNo=self.seqNo, ackNo=0, flags=FIN, checksum=0, data=b"")
        finPkt.calcChecksum()
        # send packet
        self._sendTo(finPkt) #################################
        try:
            pkt , addr = self._recvFrom() # wait for ack of fin, if we receive it we can close the socket immediately, if we timeout we will just close the socket anyway since the connection is already closed from our side and we don't care about the ack at this point
        except socket.timeout:
            print("[client] timeout waiting for ACK of FIN, closing socket anyway")
            pass
        finally:
            self.socket.close()

    def waitClose(self):
        # called by the server to wait for FIN and sen ACK
        try:
            pkt , addr = self._recvFrom() # wait for fin, if we receive it we can send ack and close the socket, if we timeout we will just close the socket anyway since the connection is already closed from the client's side and we don't care about the fin at this point
            if pkt and pkt.flags == FIN:
                ackPkt = packet(
                    seqNo=0,
                    ackNo=(self.seqNo + 1) & 0xFFFF,
                    flags=ACK,
                    checksum=0,
                    data=b"",
                )
                ackPkt.calcChecksum()
                # send packet
                self.socket.sendto(ackPkt.toBytes(),addr)
        except socket.timeout:
            print("[server] timeout waiting for FIN, closing socket anyway")
        finally:
            self.socket.close()

    def _dest(self):
        if self.destIP:
            return (self.destIP, self.destPort)
        return self.peerAddr
 
    def _sendTo(self, pkt):
        self.socket.sendto(pkt.toBytes(), self._dest())
 
    def _recvFrom(self):
        raw, addr = self.socket.recvfrom(1024)  # note 2.1
        return packet.fromBytes(raw), addr


# -- documentation --
# 1. what are structs? : They are used to pack multiple of values of different types into a fixed block of bytes
# in memory, everything is bytes. If you want to send the number 5 and the number 300 together, how does the receiver know where one ends and the other begins?
# Struct solves this by saying:
# "The first 2 bytes are the seq number, the next 2 bytes are the ack number, the next 1 byte is flags..."
# So both sender and receiver agree on the format in advance and can read the bytes correctly.
# * UDP sends and receives raw bytes so we need a way to convert our packet fields into bytes and back reliably.

# ----
# format characters that struct uses to know how many bytes to allocate:
# H : Half word = unsigned short = 2 bytes
# B : Byte = unsigned char = 1 byte
# I : Integer = unsigned int = 4 bytes
# Seq #: 2 bytes (16 bits)
# Ack #: 2 bytes (16 bits)
# Flags: 1 byte (3 flags: SYN,ACK,FIN 3 bits)
# Checksum: 2 bytes
# Data: variable


# ----
# bind to '' (empty string) which means all available network interfaces on the machine.  we accept packets coming in on any interface
# This is the standard practice because:
# The OS knows the machine's own IP already
# We don't hardcode it so the code works on any machine
# The destination needs an IP because we need to know where to send, but the source IP is just our own machine

# ----
# note 2.1
# The OS keeps a temporary memory space (buffer) where incoming packets wait until code reads them. 1024 just means "read at most 1024 bytes from that buffer at once".


# ------ important note ---  why isn't in the 3 way handshake in the 3rd step we send a body in the payload?
# In HTTP 1.0 the client sends the GET/POST request after the handshake is complete, as a separate packet. The handshake is purely for establishing the connection.
# 1. SYN          : no data
# 2. SYNACK       : no data
# 3. ACK          : no data
# 4. GET /index.html HTTP/1.0  : actual request
