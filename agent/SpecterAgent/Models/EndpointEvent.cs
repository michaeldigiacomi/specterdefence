namespace SpecterAgent.Models;

public class EndpointEvent
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string EventType { get; set; } = string.Empty;
    public string Severity { get; set; } = "MEDIUM";
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? ProcessName { get; set; }
    public string? CommandLine { get; set; }
    public string? UserContext { get; set; }
    public string? SourceIp { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
    public DateTime DetectedAt { get; set; }
}
