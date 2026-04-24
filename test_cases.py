import unittest
from udpWithRdt import packet, SYN

class TestRDTProtocol(unittest.TestCase):
    
    def test_checksum_calculation(self):
        print("\n\n=== TEST 1: Checksum Calculation ===")
        pkt = packet(seqNo=1, ackNo=0, flags=SYN, checksum=0, data=b"Test Data")
        
        print("1. Packet created with 0 checksum:")
        print(f"   {pkt}")
        
        print("2. Calculating Checksum...")
        pkt.calcChecksum()
        
        print("3. Packet after calculation:")
        print(f"   {pkt}")
        
        self.assertNotEqual(pkt.checksum, 0, "Checksum was not calculated properly.")
        self.assertTrue(pkt.verifyChecksum(), "verifyChecksum failed on a valid packet.")
        print(">>> TEST 1 PASSED!")

    def test_packet_corruption(self):
        print("\n\n=== TEST 2: Packet Corruption Detection ===")
        pkt = packet(seqNo=2, ackNo=0, flags=SYN, checksum=0, data=b"Important Data")
        pkt.calcChecksum()
        
        print("1. Original Valid Packet:")
        print(f"   {pkt}")
        
        print("2. Simulating 100% network corruption...")
        pkt.simulateCorruption(probability=1.0)
        
        print("3. Corrupted Packet (Notice the altered Checksum):")
        print(f"   {pkt}")
        
        print("4. Verifying Checksum...")
        is_valid = pkt.verifyChecksum()
        print(f"   Result: {is_valid} (Expected: False)")
        
        self.assertFalse(is_valid, "verifyChecksum failed to detect a corrupted packet.")
        print(">>> TEST 2 PASSED!")

    def test_packet_serialization(self):
        print("\n\n=== TEST 3: Packet Serialization (Bytes Conversion) ===")
        original_pkt = packet(seqNo=5, ackNo=10, flags=SYN, checksum=0, data=b"Hello")
        original_pkt.calcChecksum()
        
        print("1. Original Packet:")
        print(f"   {original_pkt}")
        
        print("2. Converting to Raw Bytes for network transfer...")
        raw_bytes = original_pkt.toBytes()
        print(f"   Bytes: {raw_bytes}")
        
        print("3. Unpacking Bytes back into a Packet object...")
        rebuilt_pkt = packet.unpackBytesToPkt(raw_bytes)
        print(f"   Rebuilt: {rebuilt_pkt}")
        
        self.assertEqual(original_pkt.seqNo, rebuilt_pkt.seqNo)
        self.assertEqual(original_pkt.data, rebuilt_pkt.data)
        print(">>> TEST 3 PASSED!\n")

if __name__ == '__main__':
    unittest.main(verbosity=2)