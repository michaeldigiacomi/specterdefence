using System.Net.Http.Json;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using SpecterAgent.Models;

namespace SpecterAgent.Services;

public class EnrollmentService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<EnrollmentService> _logger;
    private readonly string _configPath;
    private AgentConfig? _config;

    public EnrollmentService(HttpClient httpClient, ILogger<EnrollmentService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
        LoadConfig();
    }

    public bool IsEnrolled => _config?.DeviceToken != null;
    public AgentConfig? Config => _config;

    private void LoadConfig()
    {
        if (File.Exists(_configPath))
        {
            try
            {
                var json = File.ReadAllText(_configPath);
                _config = JsonConvert.DeserializeObject<AgentConfig>(json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load agent configuration.");
            }
        }
    }

    public async Task<bool> EnrollAsync(string enrollmentToken, string backendUrl)
    {
        _logger.LogInformation("Attempting to enroll device with hostname {Hostname}...", Environment.MachineName);

        var request = new
        {
            hostname = Environment.MachineName,
            os_version = Environment.OSVersion.ToString(),
            agent_version = "1.0.0",
            enrollment_token = enrollmentToken
        };

        try
        {
            var response = await _httpClient.PostAsJsonAsync($"{backendUrl}/endpoints/enroll", request);
            if (response.IsSuccessStatusCode)
            {
                var result = await response.Content.ReadFromJsonAsync<EnrollmentResponse>();
                if (result != null)
                {
                    _config = new AgentConfig
                    {
                        DeviceId = result.DeviceId,
                        DeviceToken = result.DeviceToken,
                        Hostname = Environment.MachineName,
                        BackendUrl = backendUrl
                    };
                    File.WriteAllText(_configPath, JsonConvert.SerializeObject(_config, Formatting.Indented));
                    _logger.LogInformation("Device enrolled successfully. Device ID: {DeviceId}", result.DeviceId);
                    return true;
                }
            }
            else
            {
                var error = await response.Content.ReadAsStringAsync();
                _logger.LogError("Enrollment failed: {Error}", error);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error during enrollment.");
        }

        return false;
    }

    private class EnrollmentResponse
    {
        [JsonProperty("device_id")]
        public Guid DeviceId { get; set; }
        [JsonProperty("device_token")]
        public string DeviceToken { get; set; } = string.Empty;
    }
}
