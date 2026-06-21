#!/usr/bin/env python3
import subprocess
import json

# Copy test ZIP
subprocess.run(
    ["docker", "exec", "dependency-agent-worker", "cp", 
     "/app/data/uploads/job1/simple-java-maven-app-master.zip", "/tmp/test.zip"],
    check=True
)

# Run analysis in container
cmd = '''
import requests
import json

with open("/tmp/test.zip", "rb") as f:
    files = {"file": f}
    data = {"jobId": "final-test", "projectName": "maven-test"}
    resp = requests.post("http://localhost:8123/worker/analyze-upload", files=files, data=data)
    result = resp.json()
    
    # Extract key info
    deps = result.get("report", {}).get("dependencies", [])
    summary = result.get("report", {}).get("summary", {})
    vulns_by_dep = {}
    
    for dep in deps:
        vid = dep.get("dependencyId", "")
        cat = dep.get("category", "")
        priority = dep.get("priority", "")
        vulns_by_dep[vid] = {"category": cat, "priority": priority}
    
    print("SUMMARY:", json.dumps(summary))
    print("SAMPLE_DEPS:", json.dumps(vulns_by_dep, indent=2))
    print("VULNERABILITIES_FOUND:", result.get("report", {}).get("agentTrace", {}).get("toolEvidence", {}).get("vulnerabilityCount", 0))
'''

result = subprocess.run(
    ["docker", "exec", "dependency-agent-worker", "python3", "-c", cmd],
    capture_output=True, text=True, timeout=180
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-1000:])
