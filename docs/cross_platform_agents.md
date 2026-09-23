# Cross-Platform Endpoint Agents

This document outlines the planned implementation of Linux and Mac endpoint agents for SpecterDefence to complement the existing Windows agent.

## Current Status

The Windows agent exists and monitors:
- Event ID 4688 (Process Creation) in Windows Security Logs
- Event ID 4104 (PowerShell Script Block) in PowerShell Operational Logs
- Detects suspicious patterns: `-enc`, `iex`, `downloadstring`, `certutil`, `curl`

## Planned Implementation

### Linux Agent (`SpecterAgent-Linux`)

**Architecture**: 
- .NET 8.0 cross-platform executable (runtime identifier: `linux-x64`)
- Self-contained deployment using single-file publishing
- Uses existing shared components from `SpecterAgent` project

**Monitoring Approaches**:
1. **Log File Monitoring**: Monitor system logs in `/var/log/` for security events
2. **Systemd Journal**: Use `systemd-journal-remote` to capture process creation events 
3. **Custom Pattern Detection**: Parse command line arguments for suspicious patterns

**Key Features**:
- Process event collection from Linux systems
- PowerShell script block monitoring (when available)
- Local buffering with SQLite persistence
- Silent enrollment using CLI flags
- Heartbeat service for device status reporting

### Mac Agent (`SpecterAgent-Mac`)

**Architecture**:
- .NET 8.0 cross-platform executable (runtime identifier: `osx-x64`)
- Self-contained deployment using single-file publishing
- Uses existing shared components from `SpecterAgent` project

**Monitoring Approaches**:
1. **Unified Logging System**: Use macOS unified logging APIs
2. **Console.app Integration**: Leverage system logs
3. **Process Monitoring**: Detect command line patterns similar to Windows 

**Key Features**:
- Process creation monitoring 
- PowerShell script block detection (when available)
- Local database persistence with SQLite
- Silent enrollment capabilities
- Heartbeat service for connectivity status

## Implementation Plan

### Phase 1: Shared Architecture (Completed)
- Created shared `SpecterAgent` NuGet package with core components
- Implemented cross-platform data models and interfaces
- Established common logging, configuration, and database interfaces

### Phase 2: Cross-Platform Infrastructure
- Create Linux and Mac specific executables 
- Implement platform-specific process monitoring 
- Add service management scripts for automatic startup

### Phase 3: Feature Completion
- Complete log monitoring implementations 
- Integrate with backend API for telemetry upload
- Implement full enrollment and heartbeat functionality

## Code Structure

```
agent/
├── SpecterAgent/              # Core shared components (.NET Class Library)
│   ├── Models/                # Data models (EndpointEvent, AgentConfig)
│   ├── Services/              # Shared services (Enrollment, Heartbeat, Telemetry)
│   └── Data/                  # Database context and local storage
├── SpecterAgent-Linux/        # Linux-specific implementation
│   ├── Program.cs
│   └── Services/
└── SpecterAgent-Mac/          # Mac-specific implementation  
    ├── Program.cs
    └── Services/
```

## Cross-Platform Considerations

### File System
- Local storage paths: `~/.specter/` on Unix systems instead of Windows-specific paths
- Configuration directory structure should be cross-platform

### Service Management
- Linux: systemd service files for automatic startup
- Mac: launchd plist files for automatic startup

### Dependencies 
- All agents target .NET 8.0
- Common core libraries (SQLite, HTTP Client, JSON, etc.)
- Platform-specific event monitoring APIs

This cross-platform implementation will provide comprehensive endpoint monitoring across Microsoft 365 environments while maintaining architectural consistency with the existing Windows agent.