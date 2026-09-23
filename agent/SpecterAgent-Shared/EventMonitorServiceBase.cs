using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using SpecterAgent.Models;

namespace SpecterAgent.Services;

public abstract class EventMonitorServiceBase : BackgroundService
{
    protected readonly TelemetryUploader _uploader;
    protected readonly ILogger<EventMonitorServiceBase> _logger;

    protected EventMonitorServiceBase(TelemetryUploader uploader, ILogger<EventMonitorServiceBase> logger)
    {
        _uploader = uploader;
        _logger = logger;
    }

    /// <summary>
    /// Determines if a command line is suspicious based on common attack patterns
    /// </summary>
    protected bool IsSuspicious(string? cmdLine)
    {
        if (string.IsNullOrEmpty(cmdLine)) return false;
        var lower = cmdLine.ToLower();
        return lower.Contains("-enc") || 
               lower.Contains("iex") || 
               lower.Contains("downloadstring") || 
               lower.Contains("certutil") || 
               lower.Contains("curl");
    }

    /// <summary>
    /// Processes a suspicious event and enqueues it for upload
    /// </summary>
    protected void ProcessSuspiciousEvent(string eventType, EndpointEvent payload)
    {
        try
        {
            _uploader.EnqueueEvent(payload);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing suspicious event {EventType}", eventType);
        }
    }
}