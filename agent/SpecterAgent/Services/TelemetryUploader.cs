using System.Net.Http.Headers;
using System.Net.Http.Json;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using SpecterAgent.Data;
using SpecterAgent.Models;

namespace SpecterAgent.Services;

public class TelemetryUploader : BackgroundService
{
    private readonly EnrollmentService _enrollment;
    private readonly HttpClient _httpClient;
    private readonly ILogger<TelemetryUploader> _logger;
    private readonly DatabaseContext _db;
    private readonly TimeSpan _checkInterval = TimeSpan.FromSeconds(30);

    public TelemetryUploader(
        EnrollmentService enrollment,
        HttpClient httpClient,
        ILogger<TelemetryUploader> logger)
    {
        _enrollment = enrollment;
        _httpClient = httpClient;
        _logger = logger;
        var dbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "agent.db");
        _db = new DatabaseContext(dbPath);
    }

    public void EnqueueEvent(EndpointEvent evt)
    {
        _logger.LogDebug("Enqueuing event: {Title}", evt.Title);
        Task.Run(async () => await _db.SaveEventAsync(evt));
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Telemetry Uploader starting...");

        while (!stoppingToken.IsCancellationRequested)
        {
            if (_enrollment.IsEnrolled && _enrollment.Config != null)
            {
                await ProcessPendingEventsAsync(stoppingToken);
            }

            await Task.Delay(_checkInterval, stoppingToken);
        }
    }

    private async Task ProcessPendingEventsAsync(CancellationToken ct)
    {
        try
        {
            var pending = await _db.GetPendingEventsAsync(50);
            if (pending.Count == 0) return;

            _logger.LogInformation("Uploading {Count} buffered events...", pending.Count);

            var config = _enrollment.Config!;
            var eventsToUpload = pending.Select(x => JsonConvert.DeserializeObject<EndpointEvent>(x.EventJson)).ToList();

            using var request = new HttpRequestMessage(HttpMethod.Post, $"{config.BackendUrl}/endpoints/events");
            request.Headers.Add("X-Device-Token", config.DeviceToken);
            request.Content = JsonContent.Create(new { events = eventsToUpload });

            var response = await _httpClient.SendAsync(request, ct);
            if (response.IsSuccessStatusCode)
            {
                _logger.LogInformation("Successfully uploaded {Count} events.", pending.Count);
                await _db.DeleteEventsAsync(pending.Select(x => x.Id));
            }
            else
            {
                var error = await response.Content.ReadAsStringAsync();
                _logger.LogError("Failed to upload events: {StatusCode} - {Error}", response.StatusCode, error);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing event upload.");
        }
    }
}
