"""Maven SBOM generation, upgrade detection, and OSV vulnerability scanning."""

from pathlib import Path
import json
import sys

import re

from app.tools.command_tools import runCommand

CYCLONEDX_GOAL="org.cyclonedx:cyclonedx-maven-plugin:2.8.2:makeBom"

def generateSbom(projectRoot:str)-> dict:
    """Run cyclonedx-maven-plugin to generate an SBOM and parse it into structured data."""
    # First ensure all dependencies are resolved
    runCommand(["mvn","-q","dependency:resolve","-DincludeScope=test"],projectRoot)
    # Then generate the BOM
    result=runCommand(["mvn","-q",CYCLONEDX_GOAL,"-DoutputFormat=json"],projectRoot)
    bomPath=Path(projectRoot)/"target"/"bom.json"
    sys.stderr.write(f"DEBUG generateSbom: success={result.get('success')}, bomPath exists={bomPath.exists()}\n")
    sys.stderr.flush()
    if result["success"] and bomPath.exists():
        with bomPath.open(encoding="utf-8") as f:
            bom_data=json.load(f)
            sys.stderr.write(f"DEBUG generateSbom: loaded bom with {len(bom_data.get('components',[]))} components\n")
            sys.stderr.flush()
            return {"success":True, "path":str(bomPath),"bom":bom_data,"command":result}
        
    sys.stderr.write(f"DEBUG generateSbom: SBOM generation failed - stderr={result.get('stderr','')[:100]}\n")
    sys.stderr.flush()
    return {"success":False, "path":str(bomPath),"bom":None, "errors":[f"Failed to generate SBOM: {result['stderr']}"]}
def dependenciesFromSbom(sbom:dict)-> list[dict]:
    """Extract dependencies from CycloneDX SBOM format into a simplified internal format."""
    components=sbom.get("components",[]) if sbom else []
    sys.stderr.write(f"DEBUG dependenciesFromSbom: sbom={bool(sbom)}, components count={len(components)}\n")
    sys.stderr.flush()
    dependencies=[]
    for comp in components:
        groupId,artifactId=splitMavenName(comp.get("group"),comp.get("name"))
        dependencyId=f"{groupId}:{artifactId}" if groupId else artifactId
        dependencies.append(
            {"dependencyId": dependencyId,
                "groupId": groupId,
                "artifactId": artifactId,
                "currentVersion": comp.get("version"),
                "latestVersion": None ,
                "recommendedVersion": None,
                "scope": comp.get("scope"),
                "dependencyType": "UNKNOWN",
                "licenses": extractLicenses(comp),
                "purl": comp.get("purl"),
                "priority": "LOW",
                "category": "NO_KNOWN_VULNERABILITIES",
                "fixStrategy": "MANUAL_REVIEW_REQUIRED",
                "reason": "No known vulnerabilities",
            

 
            }


            
        )
    return dependencies



def detectUpgradeCandidates(projectRoot:str,dependencies:list[dict])-> dict:
    """Detect which dependencies have newer versions available via the Maven Versions plugin."""
    commands={
        "dependencyUpdates":runCommand(["mvn","-q","versions:display-dependency-updates","-DprocessDependencyManagement=true"],cwd=projectRoot),
        "pluginUpdates":runCommand(["mvn","-q","versions:display-plugin-updates"],cwd=projectRoot),
        "propertyUpdates":runCommand(["mvn","-q","versions:display-property-updates"],cwd=projectRoot)
    }
    return {
        "dependencyUpdates": parseVersionsPluginOutput(commands["dependencyUpdates"]["stdout"]),
        "pluginUpdates": parseVersionsPluginOutput(commands["pluginUpdates"]["stdout"]),
        "propertyUpdates": parseVersionsPluginOutput(commands["propertyUpdates"]["stdout"]),
        "commands": commands
    }


def scanVulnerabilities(projectRoot:str,sbomPath:str)-> dict:
    """Scan for vulnerabilities using the OSV scanner CLI against the SBOM."""
    if not sbomPath or not Path(sbomPath).exists():
        return {"success":False,"vulnerabilities":[],"error":["SBOM path not provided for vulnerability scan"]}

    result=runCommand(["osv-scanner","--format","json","--sbom",sbomPath],cwd=projectRoot)
    if result["exitCode"]==127:
        return {"success":False,"vulnerabilities":[],"error":["OSV Scanner not found. Please ensure it is installed and in the system PATH."], "command": result}

    try:
        parsed=json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError as exc:
        parsed={}
    return {"success":result["exitCode"] in [0,1],"vulnerabilities":normalizeOsvResults(parsed),"command":result}

def runMavenTests(projectRoot:str)-> dict:
    """Run ``mvn test`` and capture results for validation and self-correction."""
    result=runCommand(["mvn","test"],cwd=projectRoot)
    return result
        
def splitMavenName(group:str | None,name:str | None)-> tuple[str | None,str | None]:
    """Split Maven group and artifact names, handling common coordinate patterns."""
    if group:
        return group, name or ""
    if name and ":" in name:
        group, artifact = name.rsplit(":", 1)
        return group, artifact
    return group, name or ""


def extractLicenses(component:dict)-> list[str]:
    """Extract license names from CycloneDX component data."""
    licenses=component.get("licenses",[])
    extracted=[]
    for lic in licenses:
        data=lic.get("license",{})
        value=data.get("name") or data.get("id")
        if value:
            extracted.append(value)
        
    return extracted


def parseVersionsPluginOutput(output:str)-> list[dict]:
    """Parse ``group:artifact version -> latest`` lines from the Versions plugin output."""
    updates=[]
    pattern=re.compile(r"^\s*([\w.-]+):([\w.-]+).*?([\w.-]+)\s*->\s*([\w.-]+)")
    for line in output.splitlines():
        match=pattern.search(line)
        if not match:
            continue
        groupId,artifactId,current,latest=match.groups()
        updates.append(
            {
                "dependencyId":f"{groupId}:{artifactId}",
                "groupId":groupId,
                "artifactId":artifactId,
                "currentVersion":current,  
                "latestVersion":latest,
                "upgradeType":classifyUpgradeType(current,latest),
        
            }
        )

    return updates


def classifyUpgradeType(current:str,latest:str)-> str:
    """Classify a semver change as PATCH, MINOR, MAJOR, or UNKNOWN."""
    currentParts=numeric_version_parts(current)
    latestParts=numeric_version_parts(latest)
    if not currentParts or not latestParts:
        return "UNKNOWN"
    if latestParts[0]>currentParts[0]:
        return "MAJOR"  
    if len(latestParts)>1 and len(currentParts)>1 and latestParts[1]>currentParts[1]:
        return "MINOR"
    if latestParts!=currentParts:
        return "PATCH"
    return "NONE"

def numeric_version_parts(version:str)-> list[int]:
    """Parse leading numeric semver parts for comparison."""
    if not version:
        return []
    match=re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if not match:
        return []
    return [int(part) for part in match.groups(default="0")]

def normalizeOsvResults(raw:dict)-> list[dict]:
    """Flatten OSV JSON into per-vulnerability records with severity and fixed versions."""
    vulnerabilities=[]
    for result in raw.get("results",[]):
        packages=result.get("packages",[])
        for package in packages:
            packageInfo=package.get("package",{})
            # OSV package name format is "groupId:artifactId" for Maven
            # We need to convert to proper PURL format: pkg:maven/groupId/artifactId
            name=packageInfo.get("name","")
            version=packageInfo.get("version","")
            ecosystem=packageInfo.get("ecosystem","")
            
            if ecosystem.lower()=="maven" and name and ":" in name:
                group,artifact=name.split(":",1)
                purl=f"pkg:maven/{group}/{artifact}@{version}" if version else f"pkg:maven/{group}/{artifact}"
            else:
                purl=None
            
            dependencyId=purlToDependencyId(purl)
            vulnCount=len(package.get("vulnerabilities",[]))
            for vuln in package.get("vulnerabilities",[]):
                severity=inferOsvSeverity(vuln)
                vulnerabilities.append(
                    {
                        "dependencyId": dependencyId,
                        "vulnerabilityId": vuln.get("id"),
                        "aliases": vuln.get("aliases",[]),
                        "summary": vuln.get("summary"),
                        "details": vuln.get("details"),
                        "severity": severity,
                        "priority": severityToPriority(severity),
                        "fixedVersions": extractFixedVersions(vuln),
                        "references": [ref.get("url") for ref in vuln.get("references",[]) if ref.get("url")],
                    }
                )           
    return vulnerabilities

def purlToDependencyId(purl:str | None)-> str | None:
    """Convert a ``pkg:maven/...`` PURL to ``groupId:artifactId``."""
    if not purl:
        return None
    match=re.match(r"pkg:maven/([^/]+)/([^@]+)(?:@(.+))?", purl)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    return None

def inferOsvSeverity(vuln:dict)-> str:
    """Map OSV severity scores to CRITICAL, HIGH, MEDIUM, or LOW."""
    severities=vuln.get("severity",[])
    for item in severities:
        score=item.get("score","")
        if "CRITICAL" in score.upper():
            return "CRITICAL"
        if "HIGH" in score.upper():
            return "HIGH"
        if "MEDIUM" in score.upper():
            return "MEDIUM"
        if "LOW" in score.upper():
            return "LOW"    
        return "UNKNOWN"

def severityToPriority(severity:str)-> str:
    """Map a severity string to a priority level (defaults to MEDIUM)."""
    if severity in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        return severity
    return "MEDIUM"

def extractFixedVersions(vuln:dict)-> list[str]:
    """Collect fixed version events from OSV affected ranges."""
    fixed=[]
    for affected in vuln.get("affected",[]):
        for range in affected.get("ranges",[]):
            for event in range.get("events",[]):
                if event.get("fixed"):
                    fixed.append(event.get("fixed"))
    return sorted(set(fixed), key=versionSortKey)

def versionSortKey(version:str)-> tuple:
    """Sort Maven-ish versions by numeric parts first, then original string."""
    numeric=[int(part) for part in re.findall(r"\d+", version or "")]
    return (numeric, version or "")
