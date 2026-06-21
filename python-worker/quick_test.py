import requests
import json

with open('/app/data/uploads/job1/simple-java-maven-app-master.zip', 'rb') as f:
    files = {'file': f}
    data = {'jobId': 'purl-fixed-test-3', 'projectName': 'test'}
    resp = requests.post('http://localhost:8123/worker/analyze-upload', files=files, data=data)
    result = resp.json()
    
    print('=' * 60)
    print('ANALYSIS RESULT')
    print('=' * 60)
    print('Success:', result.get('success'))
    print('Status:', result.get('status'))
    print('Message:', result.get('message'))
    print('Errors:', result.get('errors'))
    
    report = result.get('report', {})
    summary = report.get('summary', {})
    vuln_count = report.get('agentTrace', {}).get('toolEvidence', {}).get('vulnerabilityCount')
    tool_status = report.get('toolStatus', {})
    
    print('\nTool Status:')
    print('  SBOM Generated:', tool_status.get('sbomGenerated'))
    print('  Vulnerability Scan Success:', tool_status.get('vulnerabilityScanSuccess'))
    print('  Upgrade Detection Success:', tool_status.get('upgradeDetectionSuccess'))
    
    print('\nSummary:')
    print('  Total Dependencies:', summary.get('totalDependencies'))
    print('  Vulnerability Count (OSV Found):', vuln_count)
    print('  Categories:', summary.get('categories'))
    
    print('\nFirst 5 Dependencies:')
    deps = report.get('dependencies', [])
    if not deps:
        print('  (No dependencies)')
    for dep in deps[:5]:
        print(f"  {dep.get('dependencyId')}")
        print(f"    priority: {dep.get('priority')}, category: {dep.get('category')}")
        print(f"    vulnerabilityIds: {dep.get('vulnerabilityIds', [])}")
        print()
