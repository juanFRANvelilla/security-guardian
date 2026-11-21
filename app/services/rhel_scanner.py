import logging
from typing import List, Dict, Optional
import paramiko

from app.config import settings
from app.services.alert_store import alert_store

logger = logging.getLogger(__name__)


class RHELScanner:
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or settings.HOST_SSH_HOST
        self.username = username or settings.HOST_SSH_USER
        self.password = password or settings.HOST_SSH_PASSWORD

    def check_security_updates(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Connects to the RHEL 10 host via SSH and queries `dnf updateinfo list sec`.
        Returns newly detected security advisories grouped by severity.
        """
        if not self.host or not self.username:
            logger.warning("RHEL Scanner disabled: HOST_SSH_HOST or HOST_SSH_USER not configured.")
            return {}

        results = {
            "critical": [],
            "important": [],
            "moderate": [],
        }

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            logger.info(f"Connecting to host {self.host} to check DNF security advisories...")
            client.connect(
                self.host,
                username=self.username,
                password=self.password,
                timeout=10,
                banner_timeout=10,
            )

            stdin, stdout, stderr = client.exec_command("dnf updateinfo list sec 2>/dev/null", timeout=45)
            output = stdout.read().decode()
            client.close()

            lines = [l.strip() for l in output.strip().split("\n") if "RHSA-" in l]

            for line in lines:
                parts = line.split(maxsplit=2)
                if len(parts) >= 3:
                    rhsa, sev_raw, pkg = parts[0], parts[1], parts[2]
                    alert_id = f"rhel_{rhsa}_{pkg}"

                    if alert_store.is_seen(alert_id):
                        continue

                    item = {
                        "id": alert_id,
                        "rhsa": rhsa,
                        "package": pkg,
                    }

                    if "Critical" in sev_raw:
                        results["critical"].append(item)
                    elif "Important" in sev_raw:
                        results["important"].append(item)
                    elif "Moderate" in sev_raw:
                        results["moderate"].append(item)

        except Exception as e:
            logger.error(f"Error querying host DNF security updates: {e}")
            try:
                client.close()
            except Exception:
                pass

        return results
