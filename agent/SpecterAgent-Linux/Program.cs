using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using SpecterAgent;
using SpecterAgent.Services;

// Explicitly initialize SQLite provider to ensure native DLLs are loaded in single-file deployment
SQLitePCL.Batteries_V2.Init();

var builder = Host.CreateApplicationBuilder(args);

// Parse CLI arguments for silent enrollment
string? enrollmentToken = null;
string? backendUrl = null;

for (int i = 0; i < args.Length; i++)
{
    if (args[i] == "--enrollment-token" && i + 1 < args.Length)
        enrollmentToken = args[++i];
    else if (args[i] == "--backend-url" && i + 1 < args.Length)
        backendUrl = args[++i];
}

// Linux service configuration
builder.Services.AddHostedService<HeartbeatService>();
builder.Services.AddHostedService<EventMonitorServiceLinux>();
builder.Services.AddSingleton<TelemetryUploader>();
builder.Services.AddHttpClient();

var host = builder.Build();

// If CLI args provided, initialize enrollment service
if (!string.IsNullOrEmpty(enrollmentToken) && !string.IsNullOrEmpty(backendUrl))
{
    var enrollmentService = host.Services.GetRequiredService<EnrollmentService>();
    enrollmentService.InitializeFromArgs(enrollmentToken, backendUrl);
}

host.Run();