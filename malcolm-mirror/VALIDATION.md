# Validation record

Initial preparation and subsequent authorized deployment tested on 2026-11-05. The rows below distinguish offline preparation from live validation. Machine-readable results and template SHA-256 are in [tests/validation-results.json](tests/validation-results.json).

| Layer | Result | Scope |
|---|---|---|
| cfn-lint 1.59.0 | **0 errors, 0 warnings, 0 info findings** | JSON template, us-east-2; installed from PyPI only inside a removed disposable Python container |
| cfn-guard 3.2.1 | **0 violations; six focused rules passed** | IMDSv2, encrypted/disposable root, source-scoped UDP ingress/no key pair, opt-in session/full packets, explicit passive target, Amazon DNS. This is a project rule set, not general regulatory certification. Official ARM binary checksum verified inside a disposable container. |
| AWS validate-template | **PASS**, CAPABILITY_IAM declared | Non-deploying API; not resource provisioning or quota/capacity validation |
| Read-only live preflight | **PASS** | Account, attached/running supported source, same VPC/AZ, primary source IP, DNS/DHCP, Canonical AMI, active routes and no existing source session. Account-specific result is excluded from this public repository. |
| Python / shell / design checks | **PASS** | Python compile, rendered bootstrap and download helper shell syntax, template size, source safety/capture defaults. See check_design.py. |
| Actual offline Zeek 9.0.1 execution | **PASS** | Native ARM64 container, networking disabled, synthetic Ethernet/IPv4/VXLAN fixture: inner HTTP GET + 200 response, DNS query + answer, expected endpoints and tunnel association |
| Live AWS mirror delivery | **PASS for controlled outbound HTTP and DNS** | Systemd-managed 60-second capture: 115 packets, zero kernel drops; Zeek decoded exact test markers and inner endpoints. Cross-VPC inbound HTTP remains unverified. |
| Malcolm install/start/auth/UI | **NOT RUN** | Operator stage; pinned installer is prepared with SHA-256, not executed |
| XSIAM / Corelight modeling | **NOT RUN / out of scope** | No forwarding, models or dashboards changed |

`CREATE_COMPLETE` must not be treated as application readiness. Check the bootstrap marker, SSM, Zeek and deliberately generated inner flows before enabling a demo narrative. CloudFormation provisioning, IAM permissions and software egress were subsequently exercised successfully. Full Malcolm application health remains untested.

## Reproduce the meaningful offline test

No Python packages are required for the fixture or project assertions. From this directory on an Apple silicon Mac:

```sh
python3 tests/make_vxlan_fixture.py
mkdir -p tests/zeek-output
docker run --rm --network none --platform linux/arm64 \
  --cap-drop ALL --security-opt no-new-privileges --read-only \
  -v "$PWD/tests":/test:ro -v "$PWD/tests/zeek-output":/out -w /out \
  zeek/zeek@sha256:7811b9100eae46b6c493be74f378368a70c8d0c9f4c3616b1fffc4fec4ec73b2 \
  zeek -C -r /test/synthetic-vxlan.pcap LogAscii::use_json=T
python3 tests/check_design.py
```

The fixture sends no packets and contains no actual lab payloads. It uses zero checksums intentionally; `-C` is required. The ARM64 execution verifies the pinned Zeek version's parser, not the unlaunched amd64 EC2 host. Use the amd64 digest recorded in the template for the future EC2 sensor.

The pinned official Malcolm installer asset is `malcolm-26.10.0-docker_install.zip`, SHA-256 `59d951838209d17c1b5c60abbb39d581fdf6a6215bb32fdc006ff7ba5a429cb7`, obtained from the official release metadata. The helper verifies it before extraction. No credentials were generated. The AWS MCP skill response did not return a skill version, so its template attribution marker explicitly records `version-not-returned` rather than guessing.

## Live evidence: 2026-11-05 UTC

- Capture started **02:57:39** and exited **02:58:39**, `MainPID=0`, tcpdump exit status 0. The transient service reports `Result=timeout` because its configured `RuntimeMaxSec=60` expired; journal confirms graceful tcpdump exit. **115 captured, 115 received by filter, 0 kernel drops** in this test. This does not establish sustained throughput capacity.
- Deliberate DNS A query `mirror-goat-20261105024732.example.com` appears in Zeek JSON with the mirrored workload as origin and VPC resolver as responder, transaction ID 45123. Response is **NOERROR with no answers**, matching the client observation; do not relabel it NXDOMAIN.
- Deliberate outbound HTTP GET to `example.com/mirror-goat-20261105-outbound` returned **404** in curl and Zeek. HTTP host, URI, origin/responder tuple and response match. The absent page is expected for this unique marker; the response validates parsing, not application success.
- The closed capture produced 3 DNS, 5 HTTP, 23 connection and 20 tunnel records; 13 connection records carry tunnel parents. Counts describe only this file, not overall traffic coverage. Raw logs and PCAP remain private.
- Existing DVWA listener is bound to port 80 and loopback returns 302. Two five-second cross-VPC requests timed out; no expected client-to-DVWA port-80 tuple was found in this capture. The blocking point is **unconfirmed**. This experiment does not change original firewall, route, SG or application configuration. An outbound HTTP acceptance pass does not validate the inbound cross-VPC path.

### Capture lifecycle correction

The first capture used `timeout` under the snap SSM process. Kernel audit logs explicitly denied its SIGINT and later SIGTERM to the AppArmor-confined tcpdump process. The sensor alone was rebooted to end that run; the Friday absolute timer survived reboot.

The revised helper launches tcpdump as a transient **systemd service**, with `Type=exec`, `RuntimeMaxSec=60`, `TimeoutStopSec=5`, `KillSignal=SIGTERM`, and `UMask=0077`. The service manager handles lifecycle. AppArmor remains enforced and no profile or security rule was altered. The helper checks process exit and status before treating a capture as complete. The 400-MB approximate ring bound still applies; repeated directories accumulate until teardown.

[systemd service runtime limit](https://www.freedesktop.org/software/systemd/man/systemd.service.html) and [transient service lifecycle](https://www.freedesktop.org/software/systemd/man/systemd-run.html) describe this behavior. Full Malcolm UI/authentication, continuous recording, Broker delivery and XSIAM modeling remain outside this validation.

The final installed helper also passed end-to-end from SSM at 02:59:23–03:00:23 UTC: command exit 0, elapsed 60.085 seconds, 51 packets, zero kernel drops. This separately validates the wrapper's handling of the expected systemd timeout result. Final cfn-lint 1.59.0 checked all three templates with no findings; focused design checks and shell syntax passed.

Final CloudFormation update completed at **03:01:30 UTC**. Retrieved deployed template equals the local candidate. At **03:01:56 UTC**, bootstrap markers, Docker, the Friday absolute timer and the installed helper SHA-256 were verified; no tcpdump process remained, and 93 GiB was free. The precise HTTP and DNS test UIDs each link to VXLAN tunnel parents in `conn.log`, both with `conn_state=SF`; HTTP has packets in both directions and DNS has one query/one response.

### Recheck commands (sensor only)

```sh
sudo /usr/local/sbin/mirror-capture-test
sudo systemctl list-timers mirror-lab-stop.timer --no-pager
pgrep -a tcpdump  # should return no process after the bounded helper finishes
```

Use the README's isolated Zeek command on the resulting **closed** PCAP. Match the chosen marker in `http.log`/`dns.log`, then join its `uid` to `conn.log` and check `tunnel_parents`, `conn_state`, `orig_pkts`, and `resp_pkts`. Compare against the client command's HTTP status or DNS response. Do not use unrelated background HTTP records as proof that a particular attempted connection succeeded.
