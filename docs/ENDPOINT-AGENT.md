# SpecterDefence Windows Endpoint Agent

The SpecterDefence Windows Agent is a lightweight background service that extends threat detection to the endpoint layer. It monitors Windows Event Logs for suspicious activity and reports telemetry back to the SpecterDefence dashboard.

## Features (Phase 1)

- **Process Creation Monitoring**: Detects LOLBins (`certutil`, `mshta`, `regsvr32`, etc.) and suspicious execution patterns (Event ID 4688).
- **PowerShell Abuse Detection**: Captures script block content to identify encoded commands, download cradles, and obfuscated scripts (Event ID 4104).
- **Heartbeat & Health Tracking**: Reports device status (Online/Offline), OS version, and agent version every 5 minutes.
- **Resilient Telemetry**: Local SQLite buffering ensures events are preserved during network outages and uploaded automatically when connectivity is restored.
- **Silent Deployment**: MSI-compatible service that supports enrollment via command-line tokens.

---

## 1. Build Instructions

The agent is built using **.NET 8.0**. You will need the .NET 8 SDK installed on your build machine.

### 🚀 Automated Build (CI/CD)
The agent is automatically built via GitHub Actions on every push to the `agent/` directory. You can download the latest standalone `SpecterAgent.exe` from the **Actions** tab in the GitHub repository (Artifacts section).

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
- **Visibility Bridge**: This agent provides enterprise-grade process and PowerShell monitoring for tenants on **Microsoft 365 E3** or **Business Premium**, bridging the gap to E5-level security without the per-user licensing overhead.

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
For mass deployment (Intune, GPO, NinjaOne), use the CLI flags in your install script to ensure every device is enrolled immediately upon service start. MSI packaging support is available in the `build-agent` workflow output.

---

## 3. Configuration & Management

### Local Data
- **Config**: `config.json` stores the backend URL and enrollment token (until enrolled).
- **Identity**: Once enrolled, the agent stores its `DeviceId` and `DeviceToken` in `config.json`.
- **Buffer**: `agent.db` is a local SQLite database that stores events until they are successfully uploaded.

### Logs
The agent logs its own activity to the Windows **Application** event log and a local `logs/` directory if configured.

---

## 4. Verification

1.  Check the **Endpoints** page in the dashboard. Your device should appear as **Online** within 1-2 minutes.
2.  Test detection by running a suspicious command in PowerShell:
    ```powershell
    powershell.exe -EncodedCommand JABhID0gImhlbGxvIjsgd3JpdGUtZGVidWcgJGE=
    ```
3.  Verify the "PowerShell Abuse" event appears in the dashboard under the device's event feed.
