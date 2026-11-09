"""Windows SQL Server instance discovery."""

import json
import platform
import subprocess  # nosec B404
from dataclasses import dataclass


@dataclass(frozen=True)
class SqlInstance:
    service_name: str
    instance_name: str
    status: str

    @property
    def server(self) -> str:
        return (
            "localhost"
            if self.instance_name == "MSSQLSERVER"
            else (f"localhost\\{self.instance_name}")
        )


def discover_instances() -> list[SqlInstance]:
    if platform.system() != "Windows":
        raise RuntimeError("SQL Server discovery is supported only on Windows.")
    command = (
        "Get-Service -Name 'MSSQL*' -ErrorAction SilentlyContinue | "
        "Select-Object Name,Status | ConvertTo-Json -Compress"
    )
    result = subprocess.run(  # nosec B603 B607
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Could not discover SQL services.")
    if not result.stdout.strip():
        return []
    data = json.loads(result.stdout)
    if isinstance(data, dict):
        data = [data]
    instances: list[SqlInstance] = []
    for item in data:
        service_name = str(item["Name"])
        instance = (
            "MSSQLSERVER"
            if service_name == "MSSQLSERVER"
            else service_name.removeprefix("MSSQL$")
        )
        instances.append(SqlInstance(service_name, instance, str(item["Status"])))
    return instances
