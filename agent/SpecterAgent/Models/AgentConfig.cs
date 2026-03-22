namespace SpecterAgent.Models;

public class AgentConfig
{
    public Guid DeviceId { get; set; }
    public string? DeviceToken { get; set; }
    public string? Hostname { get; set; }
    public string BackendUrl { get; set; } = "http://localhost:8000"; // Should be configurable
    public string? EnrollmentToken { get; set; }
}
