# Validation record

Prepared 2026-11-05. No AWS resources were deployed and no traffic was generated on existing lab hosts. Machine-readable results and template SHA-256 are in [tests/validation-results.json](tests/validation-results.json).

| Layer | Result | Scope |
|---|---|---|
| cfn-lint 1.59.0 | **0 errors, 0 warnings, 0 info findings** | JSON template, us-east-2; installed from PyPI only inside a removed disposable Python container |
| cfn-guard 3.2.1 | **0 violations; six focused rules passed** | IMDSv2, encrypted/disposable root, source-scoped UDP ingress/no key pair, opt-in session/full packets, explicit passive target, Amazon DNS. This is a project rule set, not general regulatory certification. Official ARM binary checksum verified inside a disposable container. |
| AWS validate-template | **PASS**, CAPABILITY_IAM declared | Non-deploying API; not resource provisioning or quota/capacity validation |
| Read-only live preflight | **PASS** | Account, attached/running supported source, same VPC/AZ, primary source IP, DNS/DHCP, Canonical AMI, active routes and no existing source session. Account-specific result is excluded from this public repository. |
| Python / shell / design checks | **PASS** | Python compile, rendered bootstrap and download helper shell syntax, template size, source safety/capture defaults. See check_design.py. |
| Actual offline Zeek 9.0.1 execution | **PASS** | Native ARM64 container, networking disabled, synthetic Ethernet/IPv4/VXLAN fixture: inner HTTP GET + 200 response, DNS query + answer, expected endpoints and tunnel association |
| Live AWS mirror delivery | **NOT RUN** | Requires separately approved deployment and test traffic |
| Malcolm install/start/auth/UI | **NOT RUN** | Operator stage; pinned installer is prepared with SHA-256, not executed |
| XSIAM / Corelight modeling | **NOT RUN / out of scope** | No forwarding, models or dashboards changed |

`CREATE_COMPLETE` must not be treated as application readiness. Check the bootstrap marker, SSM, Zeek and deliberately generated inner flows before enabling a demo narrative. The AWS predeployment change-set validation, actual IAM create/pass-role permissions, current quotas/capacity, software egress and Malcolm health remain deployment gates.

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
