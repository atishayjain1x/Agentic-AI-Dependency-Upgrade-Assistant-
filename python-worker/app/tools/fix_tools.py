"""Dependency selection, POM version edits, validation, patches, and snapshots."""

from pathlib import Path
import shutil
import difflib
from lxml import etree

from app.tools.maven_tools import runMavenTests

def selectDependencies(report:dict,fixBy:str,value:str="",dependencyIds:list[str] | None=None)-> list[dict]:
    """Filter vulnerable report dependencies by IDS, CATEGORY, or ALL."""
    dependencies=report.get("dependencies",[])
    requestedIds=set(dependencyIds or [])
    selected=[]
    for dependency in dependencies:
        if not dependency.get("vulnerabilityIds"):
            continue

        if fixBy=="ALL":
             selected.append(dependency)
        elif fixBy=="IDS" and dependency.get("dependencyId") in requestedIds:
             selected.append(dependency)
        elif fixBy=="CATEGORY" and dependency.get("category","").lower()==value.lower():
            selected.append(dependency) 
        
    return selected


def applyFixStrategy(projectRoot:str,dependencies:list[dict],fixStrategy:str)-> dict:
    """Dispatch a fix strategy; only VERSION_BUMP is currently implemented."""
    if fixStrategy=="VERSION_BUMP":
        return applyVersionBumps(projectRoot,dependencies)
    return {"success":"False", "fixedDependencies": [], "failedDependencies":dependencies, "message":f"Fix strategy {fixStrategy} not implemented yet"}

def applyPlannedChanges(projectRoot:str,plannedChanges:list[dict])-> dict:
    """Apply dependency version updates directly from fixPlan.plannedChanges."""
    rootPom=Path(projectRoot)/"pom.xml"
    orignalText=rootPom.read_text(encoding="utf-8")
    updatedText=orignalText
    fixedChanges=[]
    failedChanges=[]

    for change in plannedChanges:
        if change.get("changeType")!="DEPENDENCY_VERSION_UPDATE":
            failedChanges.append({**change,"fixFailureReason":"Unsupported planned change type"})
            continue
        dependencyId=change.get("dependency") or ""
        targetVersion=change.get("toVersion")
        if ":" not in dependencyId or not targetVersion:
            failedChanges.append({**change,"fixFailureReason":"Missing dependency coordinates or target version"})
            continue
        groupId,artifactId=dependencyId.split(":",1)
        nextText,changed=updateDependencyVersionInPom(updatedText,groupId,artifactId,targetVersion)
        if changed:
            updatedText=nextText
            fixedChanges.append(change)
        else:
            failedChanges.append({**change,"fixFailureReason":"Failed to update version in pom"})

    if updatedText!=orignalText:
        rootPom.write_text(updatedText,encoding="utf-8")

    return {
        "success":bool(fixedChanges) and not failedChanges,
        "fixedDependencies":fixedChanges,
        "failedDependencies":failedChanges,
        "message":f"Applied {len(fixedChanges)} planned changes; {len(failedChanges)} failed to update"
    }

def applyVersionBumps(projectRoot:str,dependencies:list[dict])-> dict: 
    """Update dependency versions in the root pom.xml for each target dependency."""
    rootPom=Path(projectRoot)/"pom.xml"
    orignalText=rootPom.read_text(encoding="utf-8")
    updatedText=orignalText
    fixedDependencies=[]
    failedDependencies=[]

    for dependency in dependencies:
        targetVersion=dependency.get("recommendedVersion") or dependency.get("latestVersion")
        if not targetVersion:
            dependency["fixFailureReason"]="No target version available for version bump"
            failedDependencies.append(dependency)
            continue
    
        nextText,changed=updateDependencyVersionInPom(updatedText,dependency.get("groupId"),dependency.get("artifactId"),targetVersion)
        if changed:
            updatedText=nextText
            dependency["fixedVersion"]=targetVersion
            fixedDependencies.append(dependency)
        else:
            dependency["fixFailureReason"]="Failed to update version in pom"
            failedDependencies.append(dependency)
    if updatedText!=orignalText:
        rootPom.write_text(updatedText,encoding="utf-8")
    

    return {"success": bool(fixedDependencies) and not failedDependencies, "fixedDependencies": fixedDependencies, "failedDependencies": failedDependencies, "message": f"Applied version bumps to {len(fixedDependencies)} dependencies; {len(failedDependencies)} failed to update"}\



def updateDependencyVersionInPom(pomText:str,groupId:str,artifactId:str,targetVersion:str)-> tuple[str,bool]:
    """Find a dependency in POM text by coordinates and set its version element."""
    if not groupId or not artifactId:
        return pomText, False
    parser = etree.XMLParser(resolve_entities=False,no_network=True, remove_blank_text=False)
    root=etree.fromstring(pomText.encode("utf-8"), parser)
    ns={"m":root.nsmap.get(None)} if None in root.nsmap else {}
    prefix="m:" if ns else ""
    xpath=(f".//{prefix}dependency"
           f"[{prefix}groupId='{groupId}' and {prefix}artifactId='{artifactId}']"
    )
    deoendencies=root.xpath(xpath, namespaces=ns)
    changed=False
    for dependency in deoendencies:
        versionElement=dependency.find(f"{prefix}version", namespaces=ns)
        if versionElement is None:
            continue
        if versionElement.text!=targetVersion:
            versionElement.text=targetVersion
            changed=True    
    
    
    if not changed:
        return pomText, False   

    updated=etree.tostring(root, encoding="unicode", xml_declaration=False, pretty_print=True)
    if pomText.startswith("<?xml"):
        return "<?xml version='1.0' encoding='UTF-8'?>\n" + updated, True
    return updated, True


def runValidationIfNeeded(projectRoot:str)-> dict:
    """Run ``mvn test`` and wrap the result as a testResult dict."""
    result=runMavenTests(projectRoot)
    return {
        "skipped":False,
        "success":result.get("success",False),
        "exitCode":result.get("exitCode",1),
        "stdout":result.get("stdout",""),  
        "stderr":result.get("stderr",""),
    }

def writeTestLogs(artifactsPath:str,testResult:dict)-> None:
    """Write combined Maven stdout/stderr to ``maven-test.log`` under artifacts."""
    logsDir=Path(artifactsPath)/"maven-test.log"
    logsDir.write_text((testResult.get("stdout","") + testResult.get("stderr","")), encoding="utf-8")  # Clear existing logs
    return str(logsDir)

def generatePatch(orignalRoot:str,modifiedRoot:str,artifactsPath:str)-> str:
    """Write a unified diff of changed files (excluding target/) to ``upgrade.patch``."""
    patchPath=Path(artifactsPath)/"upgrade.patch"
    lines=[]

    for modifiedFile in Path(modifiedRoot).rglob("*"):
        if modifiedFile.is_dir() or "target" in modifiedFile.parts:
            continue
        relativePath=modifiedFile.relative_to(modifiedRoot)
        originalFile=Path(orignalRoot)/relativePath
        if not originalFile.exists():
            continue

        originalLines=originalFile.read_text(encoding="utf-8").splitlines(keepends=True)
        modifiedLines=modifiedFile.read_text(encoding="utf-8").splitlines(keepends=True)

        if originalLines==modifiedLines:
            continue

        lines.extend(difflib.unified_diff(originalLines, modifiedLines, fromfile=f"a/{relativePath}", tofile=f"b/{relativePath}"))
    patchPath.write_text("".join(lines), encoding="utf-8")
    return str(patchPath)   


def snapshotOrignal(sourceProjectRoot:str,jobId:str)-> str:
    """Copy the original project before fix mutations for later diff generation."""
    orignal=Path(sourceProjectRoot).resolve()
    snapshot=orignal.parent/f"{jobId}-original"
    if snapshot.exists():
        shutil.rmtree(snapshot)
    shutil.copytree(orignal, snapshot, ignore=shutil.ignore_patterns("target","*.log",".git","__pycache__"))
    return str(snapshot)
    
