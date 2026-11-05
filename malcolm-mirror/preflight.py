#!/usr/bin/env python3
"""Read-only preflight. Uses the approved isolated CLI; never deploys or logs credentials."""
import argparse, ipaddress, json, pathlib, shutil, subprocess

p=argparse.ArgumentParser()
p.add_argument('--parameters',default=str(pathlib.Path(__file__).with_name('parameters.observed.json')))
p.add_argument('--region',default='us-east-2')
p.add_argument('--profile',default='fed-cortex-demo')
p.add_argument('--expected-account',required=True)
p.add_argument('--docker',default=shutil.which('docker') or '/Users/dustingabel/.docker/bin/docker')
p.add_argument('--auth-volume',default='aws-fed-cortex-demo-auth')
a=p.parse_args()
params={x['ParameterKey']:x['ParameterValue'] for x in json.load(open(a.parameters))}
base=[a.docker,'run','--rm','-e','AWS_PAGER=','-v',a.auth_volume+':/root/.aws','public.ecr.aws/aws-cli/aws-cli:latest']
def aws(*args):
    r=subprocess.run(base+list(args)+['--profile',a.profile,'--region',a.region,'--output','json'],capture_output=True,text=True)
    if r.returncode: raise SystemExit(r.stderr)
    return json.loads(r.stdout)
def require(ok,msg):
    if not ok:raise SystemExit('BLOCKED: '+msg)
account=aws('sts','get-caller-identity')['Account']
require(account==a.expected_account,'Account does not match the intended lab.')
eni=aws('ec2','describe-network-interfaces','--network-interface-ids',params['SourceEniId'])['NetworkInterfaces'][0]
subnet=aws('ec2','describe-subnets','--subnet-ids',params['SensorSubnetId'])['Subnets'][0]
require(eni['OwnerId']==account and subnet['OwnerId']==account,'Account ownership mismatch.')
require(eni['VpcId']==params['VpcId']==subnet['VpcId'],'Source and sensor must use the same VPC.')
require(eni['AvailabilityZone']==subnet['AvailabilityZone'],'First test must stay in the same AZ.')
require(eni['InterfaceType']=='interface' and eni.get('Attachment'),'Source is not an attached ordinary ENI.')
require(str(ipaddress.ip_network(params['SourceIpv4Cidr']))==eni['PrivateIpAddress']+'/32','Source /32 mismatch.')
require(subnet['AvailableIpAddressCount']>0,'Subnet has no available addresses.')
vpc=aws('ec2','describe-vpcs','--vpc-ids',params['VpcId'])['Vpcs'][0]
resolver=str(ipaddress.ip_network(vpc['CidrBlock']).network_address+2)+'/32'
require(params['ResolverIpv4Cidr']==resolver,'Resolver /32 must be the primary VPC range plus two.')
dhcp=aws('ec2','describe-dhcp-options','--dhcp-options-ids',vpc['DhcpOptionsId'])['DhcpOptions'][0]
require(any(x['Key']=='domain-name-servers' and any(y['Value']=='AmazonProvidedDNS' for y in x['Values']) for x in dhcp['DhcpConfigurations']),'Custom DHCP DNS needs separate review.')
instance=aws('ec2','describe-instances','--instance-ids',eni['Attachment']['InstanceId'])['Reservations'][0]['Instances'][0]
require(instance['State']['Name']=='running','Source is not running.')
# Intentionally allow only the families reviewed for this lab; not a global support list.
require(instance['InstanceType'].split('.')[0] in ('t3','c5'),'Source family needs a fresh support review.')
sessions=aws('ec2','describe-traffic-mirror-sessions','--filters','Name=network-interface-id,Values='+params['SourceEniId'])['TrafficMirrorSessions']
require(not sessions,'Source already has a mirror session. Review priority/duplication rather than adding another.')
ami=aws('ec2','describe-images','--image-ids',params['UbuntuAmiId'])['Images'][0]
require(ami['OwnerId']=='099720109477' and ami['Architecture']=='x86_64' and ami['State']=='available','Expected available Canonical amd64 AMI.')
require('ubuntu-noble-24.04' in ami['Name'] and ami['RootDeviceName']=='/dev/sda1','Unexpected AMI OS or root device.')
route_tables=aws('ec2','describe-route-tables','--filters','Name=vpc-id,Values='+params['VpcId'])['RouteTables']
rt=next((x for x in route_tables if any(y.get('SubnetId')==params['SensorSubnetId'] for y in x['Associations'])),None)
if rt is None:rt=next(x for x in route_tables if any(y.get('Main') for y in x['Associations']))
require(any(x.get('GatewayId')=='local' and x['State']=='active' for x in rt['Routes']),'No active local route.')
require(any(x.get('DestinationCidrBlock')=='0.0.0.0/0' and x['State']=='active' for x in rt['Routes']),'No active default route for bootstrap/SSM.')
print(json.dumps({'status':'READ_ONLY_PREFLIGHT_PASS','account':account,'region':a.region,'source_eni':eni['NetworkInterfaceId'],'source_instance':instance['InstanceId'],'source_type':instance['InstanceType'],'vpc':params['VpcId'],'sensor_subnet':subnet['SubnetId'],'az':subnet['AvailabilityZone'],'ami':ami['ImageId'],'ami_name':ami['Name'],'route_table':rt['RouteTableId'],'limitations':['Does not prove new-sensor egress, SSM/bootstrap, service capacity, IAM deployment permissions, quotas, Malcolm readiness or traffic delivery.','Fails once this source has a session; inspect existing stack ownership before rerunning for an update.']},indent=2))
