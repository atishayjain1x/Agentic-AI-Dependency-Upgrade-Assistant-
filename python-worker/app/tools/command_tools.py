"""Shared helper for running local command-line tools."""

import subprocess
from pathlib import Path

from app.config import settings

def runCommand(command:list[str],cwd:str| Path,timeout:int |None =None)-> dict:
    """Run a command and return structured output without raising on non-zero exit."""
    workingDir=Path(cwd)
    try:
        result=subprocess.run(command,cwd=workingDir,capture_output=True,text=True,timeout=timeout or settings.commandTimeoutSeconds,
                              )
        return {
            "command":command,
            "cwd":str(workingDir),
            "exitCode":result.returncode,
            "stdout":result.stdout,
            "stderr":result.stderr,
            "success": result.returncode==0,
        }
    except FileNotFoundError as exc:
        return {
            "command":command,
            "cwd":str(workingDir),
            "exitCode":127,
            "stdout":"",
            "stderr":str(exc),
            "success":False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command":command,
            "cwd":str(workingDir),
            "exitCode":124,
            "stdout":exc.stdout or "",
            "stderr":exc.stderr or f"Command timed out after {exc.timeout} seconds",
            "success": False,
        }
