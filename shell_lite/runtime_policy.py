from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Mapping, Optional
from urllib.parse import urlparse


class PolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapabilityPolicy:
    safe_mode: bool
    allow_fs_read: bool
    allow_fs_write: bool
    allow_exec: bool
    allow_net: bool
    allow_web: bool
    allow_db: bool
    allow_py_import: bool
    allow_py_exec: bool
    allow_automation: bool
    allow_clipboard: bool
    fs_allowlist: List[str]
    net_allowlist: List[str]
    py_allowlist: List[str]
    exec_allowlist: List[str]


def _env_flag(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _split_allowlist(value: Optional[str], separators: Iterable[str]) -> List[str]:
    if not value:
        return []
    items = [value]
    for sep in separators:
        items = [p for part in items for p in part.split(sep)]
    return [p.strip() for p in items if p.strip()]


def _normalize_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.normpath(path)))


def _normalize_paths(paths: List[str]) -> List[str]:
    return [_normalize_path(p) for p in paths]


@lru_cache(maxsize=1)
def get_policy(env: Optional[Mapping[str, str]] = None) -> CapabilityPolicy:
    if env is None:
        env = os.environ

    safe_mode = _env_flag(env, "SHL_SAFE", False)
    if not safe_mode:
        return CapabilityPolicy(
            safe_mode=False,
            allow_fs_read=True,
            allow_fs_write=True,
            allow_exec=True,
            allow_net=True,
            allow_web=True,
            allow_db=True,
            allow_py_import=True,
            allow_py_exec=True,
            allow_automation=True,
            allow_clipboard=True,
            fs_allowlist=[],
            net_allowlist=[],
            py_allowlist=[],
            exec_allowlist=[],
        )

    allow_fs = _env_flag(env, "SHL_ALLOW_FS", False)
    allow_fs_read = _env_flag(env, "SHL_ALLOW_FS_READ", allow_fs)
    allow_fs_write = _env_flag(env, "SHL_ALLOW_FS_WRITE", allow_fs)
    allow_exec = _env_flag(env, "SHL_ALLOW_EXEC", False)
    allow_net = _env_flag(env, "SHL_ALLOW_NET", False)
    allow_web = _env_flag(env, "SHL_ALLOW_WEB", False)
    allow_db = _env_flag(env, "SHL_ALLOW_DB", False)
    allow_py = _env_flag(env, "SHL_ALLOW_PY", False)
    allow_py_import = _env_flag(env, "SHL_ALLOW_PY_IMPORT", allow_py)
    allow_py_exec = _env_flag(env, "SHL_ALLOW_PY_EXEC", allow_py)
    allow_automation = _env_flag(env, "SHL_ALLOW_AUTOMATION", False)
    allow_clipboard = _env_flag(env, "SHL_ALLOW_CLIPBOARD", False)

    fs_allow = _split_allowlist(env.get("SHL_FS_ALLOW"), [os.pathsep, ";", ","])
    if (allow_fs_read or allow_fs_write) and not fs_allow:
        fs_allow = [os.getcwd()]

    net_allow = _split_allowlist(env.get("SHL_NET_ALLOW"), [",", ";"])
    py_allow = _split_allowlist(env.get("SHL_PY_ALLOW"), [",", ";"])
    exec_allow = _split_allowlist(env.get("SHL_EXEC_ALLOW"), [",", ";"])

    return CapabilityPolicy(
        safe_mode=True,
        allow_fs_read=allow_fs_read,
        allow_fs_write=allow_fs_write,
        allow_exec=allow_exec,
        allow_net=allow_net,
        allow_web=allow_web,
        allow_db=allow_db,
        allow_py_import=allow_py_import,
        allow_py_exec=allow_py_exec,
        allow_automation=allow_automation,
        allow_clipboard=allow_clipboard,
        fs_allowlist=_normalize_paths(fs_allow),
        net_allowlist=[n.lower() for n in net_allow],
        py_allowlist=py_allow,
        exec_allowlist=exec_allow,
    )


def reset_policy_cache():
    get_policy.cache_clear()


def _require(condition: bool, message: str):
    if not condition:
        raise PolicyError(message)


def require_fs_read(path: str, policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_fs_read, "File reads are disabled by safe mode.")
    _require(_is_path_allowed(path, pol.fs_allowlist), "File path is not in the allowed list.")


def require_fs_write(path: str, policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_fs_write, "File writes are disabled by safe mode.")
    _require(_is_path_allowed(path, pol.fs_allowlist), "File path is not in the allowed list.")


def require_exec(cmd: str, policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_exec, "Command execution is disabled by safe mode.")
    if pol.exec_allowlist:
        _require(_is_exec_allowed(cmd, pol.exec_allowlist), "Command is not in the allowed list.")


def require_net(url: str, policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_net, "Network access is disabled by safe mode.")
    if pol.net_allowlist:
        _require(_is_url_allowed(url, pol.net_allowlist), "URL is not in the allowed list.")


def require_web(policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_web, "Web server operations are disabled by safe mode.")


def require_db(policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_db, "Database operations are disabled by safe mode.")


def require_py_import(module: str, policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_py_import, "Python imports are disabled by safe mode.")
    if pol.py_allowlist:
        _require(module in pol.py_allowlist, f"Python import '{module}' is not in the allowlist.")


def require_py_exec(policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_py_exec, "Python exec is disabled by safe mode.")


def require_automation(policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_automation, "Automation is disabled by safe mode.")


def require_clipboard(policy: Optional[CapabilityPolicy] = None):
    pol = policy or get_policy()
    _require(pol.allow_clipboard, "Clipboard access is disabled by safe mode.")


def _is_path_allowed(path: str, allowlist: List[str]) -> bool:
    if not allowlist:
        return True
    normalized = _normalize_path(path)
    return any(normalized.startswith(root + os.sep) or normalized == root for root in allowlist)


def _is_url_allowed(url: str, allowlist: List[str]) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    return any(host == allowed or host.endswith("." + allowed) for allowed in allowlist)


def _is_exec_allowed(cmd: str, allowlist: List[str]) -> bool:
    if not allowlist:
        return True
    first = cmd.strip().split(" ", 1)[0]
    return first in allowlist
