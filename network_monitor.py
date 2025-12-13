"""
Network connectivity monitor with robust error handling.
"""
import socket
import time
import logging
from typing import List

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """Monitors network connectivity and pauses operations when offline."""

    def __init__(self, check_hosts: List[str] = None, timeout: int = 5):
        """
        Initialize network monitor.

        Args:
            check_hosts: List of hosts to check for connectivity
            timeout: Timeout for connection attempts in seconds
        """
        self.check_hosts = check_hosts or [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "clob.polymarket.com"  # Polymarket API
        ]
        self.timeout = timeout
        self.is_online = False

    def check_connectivity(self) -> bool:
        """
        Check if internet connectivity is available.

        Returns:
            True if connected, False otherwise
        """
        for host in self.check_hosts:
            try:
                # Try to resolve DNS first
                if self._check_host(host):
                    if not self.is_online:
                        logger.info("✓ Network connectivity restored")
                        self.is_online = True
                    return True
            except Exception as e:
                logger.debug(f"Failed to connect to {host}: {e}")
                continue

        if self.is_online:
            logger.warning("✗ Network connectivity lost")
            self.is_online = False
        return False

    def _check_host(self, host: str, port: int = 53) -> bool:
        """
        Check connectivity to a specific host.

        Args:
            host: Hostname or IP address
            port: Port to check (default: 53 for DNS)

        Returns:
            True if host is reachable, False otherwise
        """
        try:
            socket.setdefaulttimeout(self.timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except (socket.error, socket.timeout, OSError):
            return False

    def wait_for_connection(self, check_interval: int = 10) -> None:
        """
        Block until network connectivity is restored.

        Args:
            check_interval: Seconds between connectivity checks
        """
        if self.check_connectivity():
            return

        logger.warning("⏸ Waiting for network connectivity...")

        while not self.check_connectivity():
            time.sleep(check_interval)

        logger.info("▶ Network connectivity restored, resuming operations")
