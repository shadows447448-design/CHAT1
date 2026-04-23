import os
import stat

import pytest

import password_notebook as pn


def test_validate_kdf_params_rejects_extreme_values():
    with pytest.raises(ValueError, match="memory_cost"):
        pn.validate_kdf_params({"iterations": 3, "lanes": 4, "memory_cost": pn.MAX_KDF_MEMORY_COST + 1})

    with pytest.raises(ValueError, match="iterations"):
        pn.validate_kdf_params({"iterations": 0, "lanes": 4, "memory_cost": 64 * 1024})


def test_decrypt_rejects_unsafe_kdf_before_derivation(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Argon2 should not be constructed for unsafe KDF params")

    monkeypatch.setattr(pn, "Argon2id", fail_if_called)
    vault = pn.Vault(
        version=pn.VAULT_VERSION,
        kdf={
            "iterations": 3,
            "lanes": 4,
            "memory_cost": pn.MAX_KDF_MEMORY_COST + 1,
            "salt_b64": pn.b64e(b"0" * pn.SALT_LEN),
        },
        nonce_b64=pn.b64e(b"1" * pn.NONCE_LEN),
        ciphertext_b64=pn.b64e(b"ciphertext"),
    )

    with pytest.raises(ValueError, match="memory_cost"):
        pn.decrypt_payload(vault, "correct horse battery staple")


def test_save_and_export_vault_use_owner_only_permissions(tmp_path):
    vault_path = tmp_path / "vault.json"
    export_path = tmp_path / "exported.json"
    vault = pn.Vault(
        version=pn.VAULT_VERSION,
        kdf={"iterations": 3, "lanes": 4, "memory_cost": 64 * 1024, "salt_b64": "salt"},
        nonce_b64="nonce",
        ciphertext_b64="ciphertext",
    )

    old_umask = os.umask(0o022)
    try:
        pn.save_vault(vault_path, vault)
        mode = stat.S_IMODE(vault_path.stat().st_mode)
        assert mode == pn.VAULT_FILE_MODE

        class Args:
            vault = str(vault_path)
            out = str(export_path)

        pn.cmd_export(Args)
        export_mode = stat.S_IMODE(export_path.stat().st_mode)
        assert export_mode == pn.VAULT_FILE_MODE
    finally:
        os.umask(old_umask)
