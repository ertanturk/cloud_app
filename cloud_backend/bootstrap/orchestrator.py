"""Windows bootstrap orchestration entry point."""

import getpass
import platform

from .database_provisioner import provision
from .env_manager import update_database_urls
from .instance_lock import InstanceLock
from .migration_runner import run_migrations
from .runtime import project_root, sync_dependencies, verify_runtime
from .seed_runner import ensure_first_admin, seed_telemetry
from .sql_configurator import configure_new_instance
from .sql_discovery import discover_instances
from .sql_health import wait_for_sql
from .sql_installer import install_dedicated_instance


def main() -> int:
    if platform.system() != "Windows":
        raise SystemExit("Phase 7 bootstrap supports Windows only.")
    root = project_root()
    with InstanceLock(
        root / "cloud_backend" / ".cloudstore-bootstrap.lock",
        "Local\\CloudStoreBootstrap",
    ):
        verify_runtime(root)
        sync_dependencies(root)
        instances = discover_instances()
        if instances:
            instance = next(
                (item for item in instances if item.instance_name == "CLOUDCORE"),
                instances[0],
            )
            bootstrap_password = getpass.getpass(
                f"SQL administrator password for {instance.server}: "
            )
        else:
            instance, bootstrap_password = install_dedicated_instance()
        configure_new_instance(instance, bootstrap_password)
        wait_for_sql(instance, bootstrap_password)
        core_url, telemetry_url = provision(instance, bootstrap_password)
        env_path = root / "cloud_backend" / ".env"
        update_database_urls(env_path, core_url, telemetry_url)
        run_migrations(root, core_url, telemetry_url)
        seed_telemetry(telemetry_url)
        ensure_first_admin(core_url)
    print("Bootstrap completed. Run scripts\\start.ps1 as a normal user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
