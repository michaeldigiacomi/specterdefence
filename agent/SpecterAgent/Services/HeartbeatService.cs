using System.Net.Http.Headers;
using System.Net.Http.Json;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace SpecterAgent.Services;

public class HeartbeatService : BackgroundService
{
    private readonly EnrollmentService _enrollmentService;
    private readonly HttpClient _httpClient;
    private readonly ILogger<HeartbeatService> _logger;
    private readonly TimeSpan _interval = TimeSpan.FromMinutes(5);

    public HeartbeatService(
        EnrollmentService enrollmentService,
        HttpClient httpClient,
        ILogger<HeartbeatService> logger)
    {
        _enrollmentService = enrollmentService;
        _httpClient = httpClient;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Heartbeat Service starting...");

        while (!stoppingToken.IsCancellationRequested)
        {
            if (!_enrollmentService.IsEnrolled)
            {
                // Check if there is an enrollment token in the config
                if (!string.IsNullOrEmpty(_enrollmentService.Config?.EnrollmentToken))
                {
                    _logger.LogInformation("Agent is not enrolled. Attempting enrollment immediately...");
                    await _enrollmentService.EnrollAsync(
                        _enrollmentService.Config.EnrollmentToken,
                        _enrollmentService.Config.BackendUrl);
                }
                else
                {
                    _logger.LogWarning("Agent is not enrolled and no enrollment token found. Waiting...");
                }
            }

            if (_enrollmentService.IsEnrolled && _enrollmentService.Config != null)
            {
                await SendHeartbeatAsync(stoppingToken);
            }

            await Task.Delay(_interval, stoppingToken);
        }
    }

    private async Task SendHeartbeatAsync(CancellationToken ct)
    {
        try
        {
            var config = _enrollmentService.Config!;
            using var request = new HttpRequestMessage(HttpMethod.Post, $"{config.BackendUrl}/api/v1/endpoints/heartbeat");
            request.Headers.Add("X-Device-Token", config.DeviceToken);
            request.Content = JsonContent.Create(new
            {
                agent_version = "1.0.0",
                os_version = Environment.OSVersion.ToString()
            });

            var response = await _httpClient.SendAsync(request, ct);
            if (response.IsSuccessStatusCode)
            {
                _logger.LogInformation("Heartbeat sent successfully.");
            }
            else
            {
                _logger.LogError("Heartbeat failed: {StatusCode}", response.StatusCode);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error sending heartbeat.");
        }
    }
}
