import hashlib

from cloud_backend.services.storage_service import StorageService


def test_storage_writes_checksum_and_rejects_paths_outside_root(storage_root) -> None:
    service = StorageService(str(storage_root))
    path = service.get_temp_path(3)
    content = b"cloud-store-test"

    service.write_chunk(path, content, append=False)
    checksum, size = service.compute_checksum_and_size(path)

    assert size == len(content)
    assert checksum == hashlib.sha256(content).digest()
    assert service.is_safe_path(path)
    assert not service.is_safe_path(str(storage_root.parent / "outside.txt"))


def test_storage_builds_sanitized_final_path(storage_root) -> None:
    service = StorageService(str(storage_root))

    path = service.get_final_path(4, 9, "../pdf")

    assert path.endswith("user_4\\9.pdf")
    assert service.is_safe_path(path)
