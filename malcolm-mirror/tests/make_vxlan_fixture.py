"""Harmless synthetic Ethernet/IPv4 VXLAN PCAP with inner HTTP and DNS.
No network traffic is sent. Checksums are deliberately zero; analyze with zeek -C.
"""
import pathlib, socket, struct

def ethernet(payload, kind=0x0800):
    return bytes.fromhex('020000000002020000000001') + struct.pack('!H', kind) + payload

def ip(src, dst, proto, payload):
    return struct.pack('!BBHHHBBH4s4s', 0x45, 0, 20+len(payload), 1, 0, 64, proto, 0,
                       socket.inet_aton(src), socket.inet_aton(dst)) + payload

def udp(src, dst, payload):
    return struct.pack('!HHHH', src, dst, 8+len(payload), 0) + payload

def tcp(src, dst, seq, ack, flags, data=b''):
    return struct.pack('!HHIIBBHHH', src, dst, seq, ack, 0x50, flags, 65535, 0, 0) + data

def wrap(frame):
    vxlan = b'\x08\x00\x00\x00\x00\x00\x64\x00' + frame
    return ethernet(ip('10.100.1.4', '10.100.1.200', 17, udp(55555, 4789, vxlan)))

def main():
    frames=[]
    client, server='10.150.1.199','10.100.1.4'
    def add(src,dst,sport,dport,seq,ack,flags,data=b''):
        frames.append(wrap(ethernet(ip(src,dst,6,tcp(sport,dport,seq,ack,flags,data)))))
    req=b'GET /mirror-lab-test HTTP/1.1\r\nHost: lab.example.test\r\nConnection: close\r\n\r\n'
    resp=b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK'
    add(client,server,42000,80,100,0,2)
    add(server,client,80,42000,200,101,18)
    add(client,server,42000,80,101,201,16)
    add(client,server,42000,80,101,201,24,req)
    add(server,client,80,42000,201,101+len(req),24,resp)
    add(client,server,42000,80,101+len(req),201+len(resp),17)
    add(server,client,80,42000,201+len(resp),102+len(req),17)
    query=struct.pack('!HHHHHH',123,0x100,1,0,0,0)+b'\x07example\x03com\x00'+struct.pack('!HH',1,1)
    reply=struct.pack('!HHHHHH',123,0x8180,1,1,0,0)+query[12:]+b'\xc0\x0c'+struct.pack('!HHIH',1,1,60,4)+socket.inet_aton('192.0.2.10')
    frames.append(wrap(ethernet(ip(server,'10.100.0.2',17,udp(53000,53,query)))))
    frames.append(wrap(ethernet(ip('10.100.0.2',server,17,udp(53,53000,reply)))))
    out=pathlib.Path(__file__).parent/'synthetic-vxlan.pcap'
    with out.open('wb') as f:
        f.write(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1))
        for i,frame in enumerate(frames):
            f.write(struct.pack('<IIII',1793850000,i*10000,len(frame),len(frame))+frame)
    print(out)
if __name__=='__main__':main()
