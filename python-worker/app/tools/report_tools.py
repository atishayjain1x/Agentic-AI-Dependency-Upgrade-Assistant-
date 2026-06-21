"""Deterministic analysis report building and vulnerability diffing."""

from collections import Counter,defaultdict
import re
from typing import Any

def buildAnalysisReport(jobId:str,projectName:str,
                        workspace:dict[str,Any],dependencies:list[dict[str,Any]],
                        upgradeCandidates:dict[str,Any],vulnerabilityScan:dict[str,Any],
                        errors:list[str])-> dict[str,Any]:
    """Build a deterministic report by merging SBOM, upgrades, and vulnerability data."""
    upgradesById={
        upgrade["dependencyId"]:upgrade for upgrade in upgradeCandidates.get("dependencyUpdates",[])

    }

    vulnerabilitiesById=defaultdict(list)
    for vuln in vulnerabilityScan.get("vulnerabilities",[]):
        if vuln.get("dependencyId"):
            vulnerabilitiesById[vuln["dependencyId"]].append(vuln)
    
    detailed=[
        enrichDependency(dependency, upgradesById.get(dependency.get("dependencyId")), vulnerabilitiesById.get(dependency.get("dependencyId"),[]))
        for dependency in dependencies
    ]

    categoryCounts=Counter(item["category"] for item in detailed)
    priorityCounts=Counter(item["priority"] for item in detailed)

    vulnerableDependencyIds=sorted({
        item.get("dependencyId")
        for item in detailed
        if item.get("dependencyId") and item.get("vulnerabilityIds")
    })

    return {
        "jobId": jobId,
        "projectName": projectName,
        "status":"COMPLETED" if not errors else "COMPLETED_WITH_ERRORS",
        "summary":
        {
            "totalDependencies": len(dependencies),
            "critical":priorityCounts.get("CRITICAL",0),
            "high":priorityCounts.get("HIGH",0),
            "medium":priorityCounts.get("MEDIUM",0),
            "low":priorityCounts.get("LOW",0),
            "categories": dict(categoryCounts),
        },
        "vulnerableDependencyIds": vulnerableDependencyIds,
        "dependencies": detailed,
    }

def enrichDependency(dependency:dict, upgrade:dict | None, vulnerabilities:list[dict])-> dict:
    """Add priority, category, fixStrategy, and recommendedVersion from upgrade/vuln data."""
    item=dict(dependency)
    if upgrade:
        item["latestVersion"]=upgrade.get("latestVersion")
        item["recommendedVersion"]=upgrade.get("latestVersion")
        item["upgradeType"]=upgrade.get("upgradeType")
    if vulnerabilities:
        priority=strongestPriority([v.get("priority","MEDIUM")for v in vulnerabilities])
        item["priority"]=priority
        item["category"]=f"{priority}_SECURITY"
        item["vulnerabilityIds"]=[v.get("vulnerabilityId") for v in vulnerabilities if v.get("vulnerabilityId")][:3]
        fixedVersions=sorted(
            {v for vuln in vulnerabilities for v in vuln.get("fixedVersions",[])},
            key=versionSortKey,
        )
        if fixedVersions:
            item["recommendedVersion"]=fixedVersions[-1]
        item["fixedVersionCandidates"]=fixedVersions
        item["vulnerabilities"]=[
            {
                "id":vuln.get("vulnerabilityId"),
                "aliases":vuln.get("aliases",[]),
                "severity":vuln.get("severity"),
                "priority":vuln.get("priority"),
                "summary":vuln.get("summary"),
                "fixedVersions":vuln.get("fixedVersions",[]),
                "references":vuln.get("references",[])[:3],
            }
            for vuln in vulnerabilities
        ]
        item["fixStrategy"]="VERSION_BUMP"
        item["reason"]="Security vulnerability"
        return item
    
    if upgrade:
        upgradeType=upgrade.get("upgradeType")
        upgradeDefaults={
            "PATCH":("LOW","SAFE_PATCH_UPGRADE","VERSION_BUMP"),
            "MINOR":("LOW","SAFE_MINOR_UPGRADE","VERSION_BUMP"),
            "MAJOR":("MEDIUM","MAJOR_BREAKING_UPGRADE")

        }
        if upgradeType in upgradeDefaults:
            item["priority"],item["category"],item["fixStrategy"]=upgradeDefaults[upgradeType]
        item["reason"]=f"{upgradeType} upgrade available"


    return item


def strongestPriority(priorities):
    """Return the highest severity among CRITICAL, HIGH, MEDIUM, and LOW."""
    order={"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1}
    return max(priorities,key=lambda v: order.get(v,0),default="MEDIUM")

def versionSortKey(version:str)-> tuple:
    """Sort Maven-ish versions by numeric parts first, then original string."""
    numeric=[int(part) for part in re.findall(r"\d+", version or "")]
    return (numeric, version or "")

def buildVulnerabilityDiff(beforeReport,afterReport):
    """Compare vulnerability sets between two reports: resolved, introduced, remaining."""
    before=vulnerability_index(beforeReport)
    after=vulnerability_index(afterReport)

    beforeKeys=set(before)
    afterKeys=set(after)

    resolved=sorted(beforeKeys-afterKeys)
    introduced=sorted(afterKeys-beforeKeys)
    remaining=sorted(beforeKeys & afterKeys)

    return{
        "beforeCount":len(beforeKeys),
        "afterCount":len(afterKeys),
        "resolvedCount":len(resolved),
        "introducedCount":len(introduced),
        "remainingCount":len(remaining),
        "resolved":[before[key] for key in resolved],
        "introduced":[after[key] for key in introduced],
        "remaining":[after[key] for key in remaining]
    }


def vulnerability_index(report):
    """Index ``dependencyId::vulnerabilityId`` keys to metadata for diffing."""
    indexed={}
    for d in report.get("dependencies",[]):
        for v in d.get("vulnerabilityIds",[]):
            key=f"{d.get('dependencyId')}::{v}"
            indexed[key]={
                "dependencyId":d.get("dependencyId"),
                "vulnerabilityId":v,
                "priority":d.get("priority"),
                "category":d.get("category"),
                "currentVersion":d.get("currentVersion"),
                "recommendedVersion":d.get("recommendedVersion")
            }
    return indexed
    
    
