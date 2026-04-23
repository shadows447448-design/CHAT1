#!/usr/bin/env python3
import argparse
import base64
import getpass
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


VAULT_VERSION = 1
SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32
MIN_KDF_ITERATIONS = 1
MAX_KDF_ITERATIONS = 10
MIN_KDF_LANES = 1
MAX_KDF_LANES = 16
MIN_KDF_MEMORY_COST = 8 * 1024
MAX_KDF_MEMORY_COST = 1024 * 1024
VAULT_FILE_MODE = 0o600


@dataclass
class Vault:
    version: int
    kdf: dict
    nonce_b64: str
    ciphertext_b64: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("utf-8"))


def _require_int_range(params: dict, key: str, minimum: int, maximum: int) -> int:
    value = params.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Invalid KDF parameter {key}: expected integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"Invalid KDF parameter {key}: expected {minimum}..{maximum}, got {value}")
    return value


def validate_kdf_params(params: dict) -> dict:
    return {
        "iterations": _require_int_range(params, "iterations", MIN_KDF_ITERATIONS, MAX_KDF_ITERATIONS),
        "lanes": _require_int_range(params, "lanes", MIN_KDF_LANES, MAX_KDF_LANES),
        "memory_cost": _require_int_range(params, "memory_cost", MIN_KDF_MEMORY_COST, MAX_KDF_MEMORY_COST),
    }


def derive_key(password: str, salt: bytes, params: dict) -> bytes:
    safe_params = validate_kdf_params(params)
    kdf = Argon2id(
        salt=salt,
        length=KEY_LEN,
        iterations=safe_params["iterations"],
        lanes=safe_params["lanes"],
        memory_cost=safe_params["memory_cost"],
    )
    return kdf.derive(password.encode("utf-8"))


def empty_payload() -> dict:
    return {"entries": {}, "created_at": now_iso(), "updated_at": now_iso()}


def encrypt_payload(payload: dict, password: str, kdf_params: dict) -> Vault:
    safe_kdf_params = validate_kdf_params(kdf_params)
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = derive_key(password, salt, safe_kdf_params)
    aesgcm = AESGCM(key)
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return Vault(
        version=VAULT_VERSION,
        kdf={**safe_kdf_params, "salt_b64": b64e(salt)},
        nonce_b64=b64e(nonce),
        ciphertext_b64=b64e(ciphertext),
    )


def decrypt_payload(vault: Vault, password: str) -> dict:
    safe_kdf_params = validate_kdf_params(vault.kdf)
    salt = b64d(vault.kdf["salt_b64"])
    nonce = b64d(vault.nonce_b64)
    ciphertext = b64d(vault.ciphertext_b64)
    key = derive_key(password, salt, safe_kdf_params)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))


def save_vault(path: Path, vault: Vault) -> None:
    data = {
        "version": vault.version,
        "kdf": vault.kdf,
        "nonce_b64": vault.nonce_b64,
        "ciphertext_b64": vault.ciphertext_b64,
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, VAULT_FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
        os.chmod(path, VAULT_FILE_MODE)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def load_vault(path: Path) -> Vault:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Vault(
        version=data["version"],
        kdf=data["kdf"],
        nonce_b64=data["nonce_b64"],
        ciphertext_b64=data["ciphertext_b64"],
    )


def prompt_master_password(confirm: bool = False) -> str:
    pw = getpass.getpass("请输入主口令: ")
    if confirm:
        pw2 = getpass.getpass("请再次输入主口令: ")
        if pw != pw2:
            raise ValueError("两次输入的主口令不一致")
    if len(pw) < 12:
        print("警告: 主口令长度建议至少 12 位，推荐 16+ 位。")
    return pw


def cmd_init(args):
    path = Path(args.vault)
    if path.exists():
        raise FileExistsError(f"仓库已存在: {path}")

    password = prompt_master_password(confirm=True)
    kdf_params = {
        "iterations": args.iterations,
        "lanes": args.lanes,
        "memory_cost": args.memory_cost,
    }
    vault = encrypt_payload(empty_payload(), password, kdf_params)
    save_vault(path, vault)
    print(f"已创建加密仓库: {path}")


def unlock(vault_path: Path) -> tuple[Vault, dict, str]:
    vault = load_vault(vault_path)
    password = prompt_master_password()
    payload = decrypt_payload(vault, password)
    return vault, payload, password


def cmd_list(args):
    vault_path = Path(args.vault)
    _, payload, _ = unlock(vault_path)
    entries = payload.get("entries", {})
    if not entries:
        print("无条目")
        return
    for title in sorted(entries.keys()):
        print(title)


def cmd_add(args):
    vault_path = Path(args.vault)
    vault, payload, password = unlock(vault_path)
    entries = payload.setdefault("entries", {})
    title = args.title.strip()
    if not title:
        raise ValueError("title 不能为空")

    username = input("username: ").strip()
    passwd = getpass.getpass("password: ")
    url = input("url: ").strip()
    notes = input("notes: ").strip()

    entries[title] = {
        "username": username,
        "password": passwd,
        "url": url,
        "notes": notes,
        "updated_at": now_iso(),
    }
    payload["updated_at"] = now_iso()

    new_vault = encrypt_payload(payload, password, vault.kdf)
    save_vault(vault_path, new_vault)
    print(f"已保存条目: {title}")


def cmd_get(args):
    vault_path = Path(args.vault)
    _, payload, _ = unlock(vault_path)
    title = args.title
    entry = payload.get("entries", {}).get(title)
    if not entry:
        print("未找到该条目")
        return
    print(json.dumps({"title": title, **entry}, ensure_ascii=False, indent=2))


def cmd_export(args):
    src = Path(args.vault)
    dst = Path(args.out)
    if src.resolve() == dst.resolve():
        raise ValueError("导出目标不能与源文件相同")
    shutil.copy2(src, dst)
    os.chmod(dst, VAULT_FILE_MODE)
    print(f"已导出密文仓库到: {dst}")


def build_parser():
    parser = argparse.ArgumentParser(description="离线加密密码记事本")
    sub = parser.add_subparsers(required=True)

    p_init = sub.add_parser("init", help="初始化新仓库")
    p_init.add_argument("--vault", required=True, help="仓库文件路径，如 /media/usb/myvault.vlt")
    p_init.add_argument("--iterations", type=int, default=3)
    p_init.add_argument("--lanes", type=int, default=4)
    p_init.add_argument("--memory-cost", type=int, default=64 * 1024)
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="新增/更新条目")
    p_add.add_argument("--vault", required=True)
    p_add.add_argument("--title", required=True)
    p_add.set_defaults(func=cmd_add)

    p_get = sub.add_parser("get", help="读取条目")
    p_get.add_argument("--vault", required=True)
    p_get.add_argument("--title", required=True)
    p_get.set_defaults(func=cmd_get)

    p_list = sub.add_parser("list", help="列出条目标题")
    p_list.add_argument("--vault", required=True)
    p_list.set_defaults(func=cmd_list)

    p_export = sub.add_parser("export", help="导出密文仓库")
    p_export.add_argument("--vault", required=True)
    p_export.add_argument("--out", required=True)
    p_export.set_defaults(func=cmd_export)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
