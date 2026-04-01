import logging
import re
import socket
import subprocess

_LOGGER = logging.getLogger(__name__)


def normalize_mac(mac: str) -> str:
    """Normalize MAC address to lowercase colon-separated format."""
    mac = mac.strip().lower()
    mac = mac.replace("-", ":")
    if len(mac) == 12 and ":" not in mac:
        mac = ":".join(mac[i : i + 2] for i in range(0, 12, 2))
    return mac


def get_arp_table() -> dict[str, str]:
    """Read system ARP table, returning {mac: ip} mapping."""
    result: dict[str, str] = {}
    try:
        with open("/proc/net/arp", "r") as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    ip, mac = parts[0], parts[3].lower()
                    if mac != "00:00:00:00:00:00":
                        result[mac] = ip
        return result
    except FileNotFoundError:
        pass
    except Exception as e:
        _LOGGER.warning("Failed to read /proc/net/arp: %s", e)

    try:
        output = subprocess.check_output(["arp", "-a"], timeout=5, text=True)
        pattern = r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]+)"
        for match in re.finditer(pattern, output):
            ip, mac = match.group(1), match.group(2).lower()
            if mac not in ("00:00:00:00:00:00", "(incomplete)"):
                result[mac] = ip
    except Exception as e:
        _LOGGER.warning("Failed to run arp -a: %s", e)
    return result


def check_host_online(ip: str, port: int = 80, timeout: float = 3.0) -> bool:
    """Check if a host is reachable by TCP connecting to the given port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((ip, port)) == 0
    except Exception:
        return False


def resolve_first_online_ip(
    macs: list[str], arp_table: dict[str, str] | None = None
) -> str | None:
    """Check MACs in order, return the first one whose IP is online."""
    if arp_table is None:
        arp_table = get_arp_table()
    for mac in macs:
        ip = arp_table.get(normalize_mac(mac))
        if ip and check_host_online(ip):
            return ip
    return None
