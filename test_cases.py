import unittest
from udpWithRdt import packet, SYN

class TestRDTProtocol(unittest.TestCase):
    
    def test_checksum_calculation(self):
        # Create a packet with some data
        pkt = packet(seqNo=1, ackNo=0, flags=SYN, checksum=0, data=b"Test Data")
        pkt.calcChecksum()
        
        # Checksum should not be 0 after calculation
        self.assertNotEqual(pkt.checksum, 0, "Checksum was not calculated properly.")
        
        # verifyChecksum should return True
        self.assertTrue(pkt.verifyChecksum(), "verifyChecksum failed on a valid packet.")

    def test_packet_corruption(self):
        pkt = packet(seqNo=1, ackNo=0, flags=SYN, checksum=0, data=b"Important Data")
        pkt.calcChecksum()
        
        # Simulate 100% chance of corruption
        pkt.simulateCorruption(probability=1.0)
        
        # verifyChecksum should now return False
        self.assertFalse(pkt.verifyChecksum(), "verifyChecksum failed to detect a corrupted packet.")

    def test_packet_serialization(self):
        original_pkt = packet(seqNo=5, ackNo=10, flags=SYN, checksum=0, data=b"Hello")
        original_pkt.calcChecksum()
        
        # Convert to bytes and back
        raw_bytes = original_pkt.toBytes()
        rebuilt_pkt = packet.unpackBytesToPkt(raw_bytes)
        
        # Ensure data matches after being unpacked
        self.assertEqual(original_pkt.seqNo, rebuilt_pkt.seqNo)
        self.assertEqual(original_pkt.data, rebuilt_pkt.data)

if __name__ == '__main__':
    unittest.main(verbosity=2)