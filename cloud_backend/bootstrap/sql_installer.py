"""Non-destructive SQL Server Developer installation."""

import shutil
import subprocess  # nosec B404

from .passwords import prompt_password
from .sql_discovery import SqlInstance


def install_dedicated_instance() -> tuple[SqlInstance, str]:
    if shutil.which("winget") is None:
        raise RuntimeError("winget is required to install SQL Server Developer.")
    password = prompt_password("Temporary SQL administrator password: ")
    instance_name = "CLOUDCORE"
    override = (
        "/Q /ACTION=Install /FEATURES=SQLEngine "
        f"/INSTANCENAME={instance_name} /SECURITYMODE=SQL "
        f"/SAPWD={password} /TCPENABLED=1 /TCPPORT=1433 "
        "/IACCEPTSQLSERVERLICENSETERMS"
    )
    result = subprocess.run(  # nosec B603 B607
        [
            "winget",
            "install",
            "--id",
            "Microsoft.SQLServer.2025.Developer",
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--include-unknown",
            "--override",
            override,
        ],
        check=False,
    )
    if result.returncode:
        from .sql_discovery import discover_instances

        discovered = [
            item for item in discover_instances() if item.instance_name == instance_name
        ]
        if not discovered:
            raise RuntimeError(
                "SQL Server Developer installation failed. "
                "Winget could not install or locate the CLOUDCORE service."
            )
        return discovered[0], password
    return SqlInstance(f"MSSQL${instance_name}", instance_name, "Running"), password
