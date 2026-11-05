"""Focused regression checks; not a replacement for cfn-lint or deployment tests."""
import json,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
t=json.loads((root/'sensor.template.json').read_text());r=t['Resources']
assert len((root/'sensor.template.json').read_bytes()) < 51200
assert len(t['Description'].encode()) < 1024
assert t['Parameters']['EnableMirroring']['Default']=='false'
assert r['MirrorSession']['Condition']=='MirroringEnabled'
assert 'PacketLength' not in r['MirrorSession']['Properties']
assert r['MirrorFilter']['Properties']['NetworkServices']==['amazon-dns']
assert r['MirrorTarget']['Properties']['NetworkInterfaceId']=={'Ref':'SensorEni'}
assert r['SensorEni']['Properties']['SourceDestCheck'] is True
assert r['SensorSecurityGroup']['Properties']['SecurityGroupIngress']==[{'IpProtocol':'udp','FromPort':4789,'ToPort':4789,'CidrIp':{'Ref':'SourceIpv4Cidr'}}]
s=r['Sensor']['Properties'];assert s['MetadataOptions']['HttpTokens']=='required'
assert s['BlockDeviceMappings'][0]['Ebs']['Encrypted'] is True
assert s['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'] is True
assert 'KeyName' not in s
assert not any(x['Type'] in ('AWS::EC2::Route','AWS::EC2::Subnet','AWS::EC2::VPC','AWS::EC2::SecurityGroupIngress') for x in r.values())
assert r['SensorRole']['Properties']['ManagedPolicyArns']==[{'Fn::Sub':'arn:${AWS::Partition}:iam::aws:policy/AmazonSSMManagedInstanceCore'}]
u=s['UserData']['Fn::Base64']['Fn::Sub']
assert u.index('systemctl enable --now mirror-lab-stop.timer') < u.index('apt-get update')
assert 'timeout --signal=INT 60' in u and '-C 100 -W 4' in u
with tempfile.NamedTemporaryFile(mode='w',suffix='.sh') as f:
 f.write(u.replace('${AutoShutdownMinutes}','240').replace('${SourceIpv4Cidr}','10.100.1.4/32'));f.flush();subprocess.run(['bash','-n',f.name],check=True)
print('PASS: opt-in mirroring, target wiring, scoped ingress, encrypted ephemeral disk, IMDSv2, isolated resources, SSM-only IAM, early cost timer, bounded capture, shell syntax and size.')
# Check actual Zeek output when present; the fixture generator sends no traffic.
z=root/'tests'/'zeek-output'
if (z/'http.log').exists():
 read=lambda n:[json.loads(x) for x in (z/(n+'.log')).read_text().splitlines()]
 assert any(x.get('uri')=='/mirror-lab-test' and x['id.orig_h']=='10.150.1.199' and x['id.resp_h']=='10.100.1.4' and x.get('status_code')==200 for x in read('http'))
 assert any(x.get('query')=='example.com' and x['id.orig_h']=='10.100.1.4' and x['id.resp_h']=='10.100.0.2' and x.get('answers')==['192.0.2.10'] for x in read('dns'))
 assert any(x.get('service')=='http' and x.get('tunnel_parents') for x in read('conn'))
 print('PASS: actual Zeek output has inner HTTP 200 and DNS answer with expected endpoints and VXLAN tunnel parent.')
else:print('NOT RUN: Zeek output checks (generate fixture and run container first).')
