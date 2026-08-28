# SpecterDefence Windows Endpoint Agent

The SpecterDefence Windows Agent is a lightweight background service that extends threat detection to the endpoint layer. It monitors Windows Event Logs for suspicious activity and reports telemetry back to the SpecterDefence dashboard.

## Features (Phase 1)

- **Process Creation Monitoring**: Watches Security Event ID 4688; command lines are flagged suspicious on pattern match (`-enc`, `iex`, `downloadstring`, `certutil`, `curl`). Suspicious → HIGH, otherwise LOW.
- **PowerShell Abuse Detection**: Captures script block content (Event ID 4104) to identify encoded commands and download cradles. Suspicious → HIGH, otherwise MEDIUM.
- **Heartbeat & Health Tracking**: Reports device status, OS version, and agent version every 5 minutes.
- **Resilient Telemetry**: Events are buffered in a local SQLite database (`agent.db`, in the install directory) and uploaded on a 30-second loop; entries are deleted only after the backend acknowledges them.
- **Silent Deployment**: Standalone single-file `SpecterAgent.exe` Windows service supporting enrollment tokens via CLI flags for Intune/GPO-style mass deployment.

---

## 1. Build Instructions

The agent is built using **.NET 8.0**. You will need the .NET 8 SDK installed on your build machine.

### 🚀 Automated Build (CI/CD)
The agent is built by the GitHub Actions workflow on changes under `agent/`. Download the standalone `SpecterAgent.exe` from the workflow's **Artifacts**.

### Manual Build (Single-File)
To generate a standalone executable manually:
```powershell
cd agent\SpecterAgent
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true /p:PublishTrimmed=false -o ./publish
```

---

## 2. Installation Instructions

### Prerequisites
- Windows 10/11 or Windows Server 2016+
- Administrator privileges.
- Uses native Windows APIs only — no kernel driver, no Sysmon dependency.

### Manual Installation
1.  Generate an **Enrollment Token** from the **Endpoints** page in the SpecterDefence dashboard.
2.  Copy the `SpecterAgent.exe` to a permanent location (e.g., `C:\Program Files\SpecterAgent\`).
3.  **Initialize via CLI (Recommended)**:
    Run the agent with the following flags to automatically create the configuration and enroll:
    ```powershell
    .\SpecterAgent.exe --enrollment-token YOUR_TOKEN --backend-url https://your-specter-url
    ```
4.  **Install as a Windows Service**:
    ```powershell
    sc.exe create SpecterAgent binPath= "C:\Program Files\SpecterAgent\SpecterAgent.exe" start= auto
    sc.exe start SpecterAgent
    ```

### Silent / Mass Deployment
For mass deployment (Intune, GPO, RMM), wrap `SpecterAgent.exe` in your own MSI/Intune package and pass the CLI flags in the install step so devices enroll at first service start. The CI artifact is the single-file exe only — no MSI is produced.

---

## 3. Configuration & Management

### Local Data
- **Config**: `config.json` (in the exe directory) stores the backend URL and enrollment token until enrolled.
- **Identity**: Once enrolled, the agent stores its `DeviceId` and `DeviceToken` in `config.json`.
- **Buffer**: `agent.db` (SQLite, exe directory) stores events until the backend acknowledges them.

### Logs
The agent logs through the standard .NET host logging pipeline. When run as a Windows Service, inspect via `sc.exe query SpecterAgent` and the Service Control Manager log, or run the exe directly in a console to see live output.

---

## 4. Verification

1.  Check the **Endpoints** page in the dashboard. Your device should appear as **Online** within 1-2 minutes.
2.  Test detection by running a suspicious command in PowerShell:
    ```powershell
    powershell.exe -EncodedCommand JABhID0gImhlbGxvIjsgd3JpdGUtZGVidWcgJGE=
    ```
3.  Verify the "PowerShell Abuse" event appears in the dashboard under the device's event feed.