"""
SAS Viya Execution Connector — Framework
Target: SAS OnDemand for Academics (https://welcome.oda.sas.com/)

REST API reference:
  Authentication : POST {base_url}/SASLogon/oauth/token  (OAuth2 password grant)
  Create session : POST {base_url}/compute/sessions
  Submit job     : POST {base_url}/compute/sessions/{sid}/jobs
  Poll status    : GET  {base_url}/compute/sessions/{sid}/jobs/{jid}
  Fetch logs     : GET  {base_url}/compute/sessions/{sid}/jobs/{jid}/log
  Fetch results  : GET  {base_url}/compute/sessions/{sid}/jobs/{jid}/results

Set enabled=False (default) to keep using simulated SAS execution.
Set enabled=True  once credentials are configured to route through SAS Viya.
"""

from typing import Any, Dict, List, Optional


class SasViyaExecutor:
    """
    Future-ready SAS Viya connector.  All network calls are guarded so the
    class is safe to instantiate even when the requests library is absent or
    when no credentials are provided.
    """

    def __init__(
        self,
        base_url: str = "",
        username: str = "",
        password: str = "",
        client_id: str = "sas.ec",
        client_secret: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret

        self._access_token: Optional[str] = None
        self._session_id: Optional[str] = None

    # ── Authentication ──────────────────────────────────────────────────────────

    def connect(self) -> Dict[str, Any]:
        """
        Authenticate with SAS Viya using the OAuth2 password-grant flow.
        SAS OnDemand for Academics uses client_id='sas.ec' with no secret.
        """
        if not self.base_url or not self.username:
            return {"status": "error", "message": "base_url and username are required."}
        try:
            import base64
            import requests

            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()

            resp = requests.post(
                f"{self.base_url}/SASLogon/oauth/token",
                data={
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                },
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30,
                verify=True,
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data.get("access_token")
            return {
                "status": "connected",
                "token_type": data.get("token_type", "Bearer"),
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── Job lifecycle ───────────────────────────────────────────────────────────

    def submit_job(
        self,
        sas_code: str,
        context_name: str = "SAS Studio compute context",
    ) -> Dict[str, Any]:
        """Create a compute session then submit SAS code as a job."""
        if not self._access_token:
            return {"status": "error", "message": "Not connected. Call connect() first."}
        try:
            import requests

            # 1. Create session
            sess = requests.post(
                f"{self.base_url}/compute/sessions",
                json={"context": {"name": context_name}},
                headers=self._headers(),
                timeout=30,
            )
            sess.raise_for_status()
            self._session_id = sess.json().get("id")

            # 2. Submit job
            job = requests.post(
                f"{self.base_url}/compute/sessions/{self._session_id}/jobs",
                json={"code": sas_code},
                headers=self._headers(),
                timeout=30,
            )
            job.raise_for_status()
            job_data = job.json()

            return {
                "status": "submitted",
                "job_id": job_data.get("id"),
                "session_id": self._session_id,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def check_status(self, job_id: str) -> Dict[str, Any]:
        """Poll the status of a submitted compute job."""
        if not self._session_id or not self._access_token:
            return {"status": "error", "message": "No active session."}
        try:
            import requests

            resp = requests.get(
                f"{self.base_url}/compute/sessions/{self._session_id}/jobs/{job_id}",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"status": data.get("state", "unknown"), "job_id": job_id}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def get_logs(self, job_id: str) -> Dict[str, Any]:
        """Retrieve execution log lines for a completed job."""
        if not self._session_id or not self._access_token:
            return {"status": "error", "message": "No active session.", "logs": []}
        try:
            import requests

            resp = requests.get(
                f"{self.base_url}/compute/sessions/{self._session_id}/jobs/{job_id}/log",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            lines: List[str] = [
                item.get("line", "") for item in data.get("items", [])
            ]
            return {"status": "success", "logs": lines}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "logs": []}

    def get_outputs(self, job_id: str) -> Dict[str, Any]:
        """Retrieve output dataset references for a completed job."""
        if not self._session_id or not self._access_token:
            return {"status": "error", "message": "No active session.", "outputs": []}
        try:
            import requests

            resp = requests.get(
                f"{self.base_url}/compute/sessions/{self._session_id}/jobs/{job_id}/results",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"status": "success", "outputs": data.get("items", [])}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "outputs": []}

    # ── File Upload ─────────────────────────────────────────────────────────────

    def upload_file(self, file_path: str, filename: str = "") -> Dict[str, Any]:
        """Upload a file to SAS Viya Files API."""
        if not self._access_token:
            return {"status": "error", "message": "Not connected. Call connect() first."}
        try:
            import requests
            from pathlib import Path

            if not filename:
                filename = Path(file_path).name

            with open(file_path, "rb") as f:
                files = {"files": (filename, f)}
                resp = requests.post(
                    f"{self.base_url}/files/files?typeDefName=file",
                    files=files,
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
            file_id = data.get("id") or data.get("resourceId")
            return {
                "status": "uploaded",
                "file_id": file_id,
                "file_uri": f"/files/files/{file_id}/content" if file_id else None,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # ── Job Polling ─────────────────────────────────────────────────────────────

    def wait_for_job(
        self,
        session_id: str,
        job_id: str,
        timeout: int = 300,
        interval: int = 3,
    ) -> Dict[str, Any]:
        """Poll a job until it completes or times out."""
        import time

        start = time.time()
        while time.time() - start < timeout:
            status_result = self.check_status(job_id)
            current_state = status_result.get("status", "unknown")
            if current_state in ("completed", "failed", "canceled"):
                return {"status": current_state, "job_id": job_id}
            time.sleep(interval)
        return {"status": "timeout", "job_id": job_id}

    # ── End-to-End Execution ────────────────────────────────────────────────────

    def execute(
        self,
        sas_code: str,
        dataset_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute SAS code on SAS Viya with optional dataset upload."""
        from pathlib import Path

        # 1. Connect
        conn_result = self.connect()
        if conn_result.get("status") != "connected":
            return {
                "status": "error",
                "message": f"Connection failed: {conn_result.get('message')}",
            }

        # 2. Upload datasets and collect file URIs
        file_preamble_lines: List[str] = []
        if dataset_paths:
            for idx, path_str in enumerate(dataset_paths):
                p = Path(path_str)
                if not p.exists():
                    continue
                upload_result = self.upload_file(str(p))
                if upload_result.get("status") != "uploaded":
                    return {
                        "status": "error",
                        "message": f"Failed to upload {p.name}: {upload_result.get('message')}",
                    }
                file_id = upload_result["file_id"]
                ext = p.suffix.lower()
                # Extract dataset name from path (e.g., "ae_raw" from "...ae_raw.csv")
                dset_name = p.stem.upper()
                file_ref_name = f"_f{idx}"

                # Build FILENAME + PROC IMPORT block
                file_preamble_lines.append("")
                file_preamble_lines.append(
                    f"/* Uploaded dataset: {p.name} → WORK.{dset_name} */"
                )
                file_preamble_lines.append(
                    f"filename {file_ref_name} url "
                    f'"&_svc/files/files/{file_id}/content" '
                    f'headers=("Authorization"="Bearer &_tok");'
                )
                # Detect DBMS type
                if ext == ".csv":
                    dbms = "csv"
                elif ext in (".sas7bdat", ".sas"):
                    dbms = "sas7bdat"
                elif ext == ".xpt":
                    dbms = "xport"
                else:
                    dbms = "csv"
                file_preamble_lines.append(
                    f"proc import datafile={file_ref_name} "
                    f"out=WORK.{dset_name} dbms={dbms} replace;"
                )
                if dbms == "csv":
                    file_preamble_lines.append("  getnames=yes;")
                file_preamble_lines.append("run;")

        # 3. Build final SAS code with preamble
        preamble = [
            "/* ═══════════════════════════════════════════════════════════════ */",
            "/* EvolveR: SAS Viya Execution Preamble                          */",
            "/* ═══════════════════════════════════════════════════════════════ */",
            "",
            "%let _tok=%sysget(SAS_TOKEN);",
            "%let _svc=%sysget(SAS_SERVICES_URL);",
        ]
        preamble.extend(file_preamble_lines)
        if file_preamble_lines:
            preamble.append("")
        preamble.append("/* ═══════════════════════════════════════════════════════════════ */")
        preamble.append("/* User SAS Code                                                   */")
        preamble.append("/* ═══════════════════════════════════════════════════════════════ */")
        preamble.append("")

        full_sas_code = "\n".join(preamble) + sas_code

        # 4. Submit job
        job_result = self.submit_job(full_sas_code)
        if job_result.get("status") != "submitted":
            return {
                "status": "error",
                "message": f"Job submission failed: {job_result.get('message')}",
            }

        job_id = job_result["job_id"]
        session_id = job_result["session_id"]

        # 5. Wait for job completion
        wait_result = self.wait_for_job(session_id, job_id)
        final_status = wait_result.get("status", "error")

        # 6. Fetch logs regardless of status
        log_result = self.get_logs(job_id)
        logs = log_result.get("logs", [])

        return {
            "status": final_status,
            "logs": logs,
            "job_id": job_id,
            "session_id": session_id,
        }
