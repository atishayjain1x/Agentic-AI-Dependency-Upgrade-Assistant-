"""ZIP extraction, workspace preparation, and Maven POM parsing."""

from pathlib import Path
import shutil
import zipfile
import re

from lxml import etree
from app.config import settings

class ProjectExtractionError(Exception):
    """Raised for invalid job IDs, unsafe paths, or bad ZIP extraction."""


def safeJobPath(baseDir,jobId):
    """Validate jobId and ensure the resolved path stays under baseDir."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+",jobId):
        raise ProjectExtractionError("Invalid JobId name")
    base=baseDir.resolve()
    path=(base/jobId).resolve()
    if not path.is_relative_to(base):
        raise ProjectExtractionError("job resolves outside configured dir")
    return path

def prepareWorkspace(jobId, zipPath):
    """Extract a ZIP, detect the Maven reactor root, and return workspace metadata."""
    zip_path = Path(zipPath).expanduser().resolve()
    if not zip_path.exists():
        raise ProjectExtractionError("Zip file not found")
    if zip_path.suffix.lower() != ".zip":
        raise ProjectExtractionError("Input must be a Zip file")

    if zip_path.stat().st_size > settings.maxZipBytes:
        raise ProjectExtractionError("Zip file size exceeds limit")
    
    if not zipfile.is_zipfile(zip_path):
        raise ProjectExtractionError("Zip file invalid")
    
    workspaceDir = safeJobPath(settings.workspaces_dir ,jobId)
    sourceDir = workspaceDir / "source"
    artifactDir = safeJobPath(settings.artifacts_dir ,jobId)

    if workspaceDir.exists():
        shutil.rmtree(workspaceDir)
    
    if artifactDir.exists():
        shutil.rmtree(artifactDir)
    
    sourceDir.mkdir(parents=True, exist_ok=True)
    artifactDir.mkdir(parents=True, exist_ok=True)
    safeExtractZip(zip_path, sourceDir)
    projectRoot = detectMavenReactorRoot(sourceDir)
    rootPom = projectRoot / "pom.xml"
    
    return {
        "workspacePath": str(workspaceDir),
        "sourcePath": str(sourceDir),
        "projectRoot": str(projectRoot),
        "rootPomPath": str(rootPom),
        "artifactsPath": str(artifactDir),
        "pomMetadata": parsePomMetadata(rootPom),
    }


def safeExtractZip(zipFile: Path, destination: Path) -> None:
    """Extract a ZIP with zip-slip protection and uncompressed size limits."""
    destination = destination.resolve()
    totalUnzipped = 0

    with zipfile.ZipFile(zipFile, "r") as archive:
        infos = archive.infolist()
        
        for member in infos:
            memberPath = destination / member.filename
            resolvedPath = memberPath.resolve()

            try:
                resolvedPath.relative_to(destination)
            except ValueError:
                raise ProjectExtractionError("Unsafe Zip Path Detected")

            totalUnzipped += member.file_size
            if totalUnzipped > settings.maxUnzippedBytes:
                raise ProjectExtractionError("Zip size exceeds")
    
        archive.extractall(destination)


def detectMavenReactorRoot(sourceDir: Path):
    """Find the Maven project root from an extracted source directory."""
    sourceDir = sourceDir.resolve()
    if (sourceDir / "pom.xml").exists():
        return sourceDir

    visibleChildren = [
        p for p in sourceDir.iterdir()
        if p.is_dir() and not p.name.startswith("_MACOSX") and not p.name.startswith(".")
    ]
    if len(visibleChildren) == 1 and (visibleChildren[0] / "pom.xml").exists():
        return visibleChildren[0].resolve()
    
    candidatePoms = [
        p for p in sourceDir.rglob("pom.xml")
        if "target" not in p.parts and ".git" not in p.parts
    ]

    rootCandidates = []
    for pom in candidatePoms:
        if isLikelyReactorRoot(pom):
            rootCandidates.append(pom.parent.resolve())
        
    uniqueRoots = sorted(set(rootCandidates), key=lambda p: len(p.parts))
    if len(uniqueRoots) == 1:
        return uniqueRoots[0]

    if len(uniqueRoots) > 1:
        raise ProjectExtractionError("Multiple maven reactor roots detected")

    if len(candidatePoms) == 1:
        return candidatePoms[0].parent.resolve()
    
    raise ProjectExtractionError("NO maven reactor pom found")
           
def isLikelyReactorRoot(pomPath: Path) -> bool:
    """Return True if the POM has modules or packaging=pom (multi-module parent)."""
    metadata = parsePomMetadata(pomPath)
    return metadata.get("modules") is not None or metadata.get("packaging") == "pom"

def parsePomMetadata(pomPath: Path) -> dict:
    """Parse groupId, artifactId, version, packaging, and modules from pom.xml."""
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(str(pomPath), parser)
    root = tree.getroot()
    ns={"m":root.nsmap.get(None)} if None in root.nsmap else {}

    def xpathText(xpath: str) -> str | None:
        result = root.xpath(xpath, namespaces=ns)
        if not result:
            return None
        value=result[0]
        if isinstance(value, etree._Element):
            return value.text.strip() if value.text else None
        return str(value).strip()
    
    prefix="m:" if ns else ""
    modules=[str(module).strip() for module in root.xpath(f"{prefix}modules/{prefix}module", namespaces=ns)
             if str(module).strip()]
    
    return {
        "groupId": xpathText(f"{prefix}groupId") or xpathText(f"{prefix}parent/{prefix}groupId"),
        "artifactId": xpathText(f"{prefix}artifactId"),
        "version": xpathText(f"{prefix}version") or xpathText(f"{prefix}parent/{prefix}version"),
        "packaging": xpathText(f"{prefix}packaging") or "jar",
        "modules": modules,
        "isMultiModule": bool(modules),
    }       

def copyWorkspaceForFix(sourceProjectRoot:str,jobId:str)-> dict:
    """Copy the project tree to a fix workspace, excluding build artifacts and VCS dirs."""
    originalRoot=Path(sourceProjectRoot).resolve()
    fixWorkspaceDir=safeJobPath(settings.workspaces_dir , jobId) / "fix-source"
    artifactDir=safeJobPath(settings.artifacts_dir ,jobId)

    if fixWorkspaceDir.exists():
        shutil.rmtree(fixWorkspaceDir)

    if artifactDir.exists():
        shutil.rmtree(artifactDir)

    artifactDir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(originalRoot, fixWorkspaceDir,ignore=shutil.ignore_patterns(".git",".svn",".hg","target","build",".gradle",".idea"))
    return {
        "workspacePath": str(fixWorkspaceDir),
        "projectRoot": str(fixWorkspaceDir),
        "rootPomPath": str(fixWorkspaceDir / "pom.xml"),
        "artifactsPath": str(artifactDir),
    }
