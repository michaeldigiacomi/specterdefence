using System.Diagnostics.Eventing.Reader;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using SpecterAgent.Models;

namespace SpecterAgent.Services;

public class EventMonitorService : BackgroundService
{
    private readonly TelemetryUploader _uploader;
    private readonly ILogger<EventMonitorService> _logger;
    private readonly List<EventLogWatcher> _watchers = new();

    public EventMonitorService(TelemetryUploader uploader, ILogger<EventMonitorService> logger)
    {
        _uploader = uploader;
        _logger = logger;
    }

    protected override Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Event Monitor Service starting...");

        try
        {
            // Watch Security Log for Process Creation (Event 4688)
            var securityQuery = new EventLogQuery("Security", PathType.LogName, "*[System[(EventID=4688)]]");
            var securityWatcher = new EventLogWatcher(securityQuery);
            securityWatcher.EventRecordWritten += OnEventWritten;
            securityWatcher.Enabled = true;
            _watchers.Add(securityWatcher);

            // Watch PowerShell Log for Script Block (Event 4104)
            var psQuery = new EventLogQuery("Microsoft-Windows-PowerShell/Operational", PathType.LogName, "*[System[(EventID=4104)]]");
            var psWatcher = new EventLogWatcher(psQuery);
            psWatcher.EventRecordWritten += OnEventWritten;
            psWatcher.Enabled = true;
            _watchers.Add(psWatcher);

            _logger.LogInformation("Subscribed to Security (4688) and PowerShell (4104) events.");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start one or more event watchers. Ensure the service is running as an administrator.");
        }

        return Task.CompletedTask;
    }

    private void OnEventWritten(object? sender, EventRecordWrittenEventArgs e)
    {
        if (e.EventRecord == null) return;

        try
        {
            var eventId = e.EventRecord.Id;
            var payload = new EndpointEvent
            {
                DetectedAt = e.EventRecord.TimeCreated ?? DateTime.UtcNow,
                Title = $"Event ID {eventId} detected",
                Severity = "MEDIUM" // Default
            };

            if (eventId == 4688)
            {
                payload.EventType = "suspicious_process";
                payload.Title = "Process Created";
                payload.ProcessName = e.EventRecord.Properties[5].Value.ToString(); // NewProcessName
                payload.CommandLine = e.EventRecord.Properties[8].Value.ToString(); // CommandLine
                payload.UserContext = e.EventRecord.Properties[1].Value.ToString(); // TargetUserName
                payload.Severity = IsSuspicious(payload.CommandLine) ? "HIGH" : "LOW";
            }
            else if (eventId == 4104)
            {
                payload.EventType = "powershell_abuse";
                payload.Title = "PowerShell Script Block Captured";
                payload.CommandLine = e.EventRecord.Properties[2].Value.ToString(); // ScriptBlockText
                payload.Severity = IsSuspicious(payload.CommandLine) ? "HIGH" : "MEDIUM";
            }

            _uploader.EnqueueEvent(payload);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing event record.");
        }
    }

    private bool IsSuspicious(string? cmdLine)
    {
        if (string.IsNullOrEmpty(cmdLine)) return false;
        var lower = cmdLine.ToLower();
        return lower.Contains("-enc") || lower.Contains("iex") || lower.Contains("downloadstring") || lower.Contains("certutil") || lower.Contains("curl");
    }

    public override void Dispose()
    {
        foreach (var watcher in _watchers)
        {
            watcher.Enabled = false;
            watcher.Dispose();
        }
        base.Dispose();
    }
}
