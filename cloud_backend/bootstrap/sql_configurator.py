"""Configure and verify the local SQL Server TCP endpoint."""

import os
import shutil
import socket
import subprocess  # nosec B404

from .sql_discovery import SqlInstance


def verify_port(port: int = 1433, host: str = "127.0.0.1") -> None:
    with socket.create_connection((host, port), timeout=3):
        return


def configure_new_instance(
    instance: SqlInstance, bootstrap_password: str, port: int = 1433
) -> None:
    """Enable TCP on the selected instance and bind its fixed local port."""
    command = r"""
$instanceNames = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL' -ErrorAction Stop
$instanceId = $instanceNames.PSObject.Properties[$env:CLOUD_SQL_INSTANCE].Value
if (-not $instanceId) { throw "SQL instance was not found in the registry." }
$server = "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\$instanceId\MSSQLServer"
$loginMode = Get-ItemProperty -Path $server -Name LoginMode -ErrorAction SilentlyContinue
if (-not $loginMode) { throw "SQL authentication configuration was not found." }
Set-ItemProperty -Path $server -Name LoginMode -Type DWord -Value 2
$tcp = "$server\SuperSocketNetLib\Tcp"
if (-not (Test-Path $tcp)) { throw "SQL TCP configuration path was not found." }
Set-ItemProperty -Path $tcp -Name Enabled -Type DWord -Value 1
$ipAll = Join-Path $tcp "IPAll"
Set-ItemProperty -Path $ipAll -Name TcpDynamicPorts -Value ""
Set-ItemProperty -Path $ipAll -Name TcpPort -Value $env:CLOUD_SQL_PORT
Restart-Service -Name $env:CLOUD_SQL_SERVICE -Force
"""
    environment = os.environ.copy()
    environment.update(
        {
            "CLOUD_SQL_INSTANCE": instance.instance_name,
            "CLOUD_SQL_PORT": str(port),
            "CLOUD_SQL_SERVICE": instance.service_name,
        }
    )
    result = subprocess.run(  # nosec B603 B607
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**environment},
    )
    if result.returncode:
        raise RuntimeError(
            result.stderr.strip() or "Could not configure SQL Server TCP."
        )
    verify_port(port)
    sqlcmd = shutil.which("sqlcmd")
    if sqlcmd is None:
        raise RuntimeError(
            "sqlcmd is required to enable the sa login using Windows authentication."
        )
    try:
        result = subprocess.run(  # nosec B603
            [
                sqlcmd,
                "-E",
                "-S",
                f"tcp:127.0.0.1,{port}",
                "-C",
                "-N",
                "o",
                "-b",
                "-Q",
                (
                    "IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'sa') "
                    "BEGIN ALTER LOGIN [sa] ENABLE; "
                    "ALTER LOGIN [sa] WITH PASSWORD = N'$(SAPASSWORD)'; END"
                ),
                "-v",
                f"SAPASSWORD={bootstrap_password.replace(chr(39), chr(39) * 2)}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "sqlcmd disappeared while configuring SQL Server."
        ) from error
    if result.returncode:
        raise RuntimeError(
            result.stderr.strip() or "Could not enable SQL Server authentication."
        )
