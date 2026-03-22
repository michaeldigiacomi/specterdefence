using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using SpecterAgent;
using SpecterAgent.Services;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddWindowsService(options =>
{
    options.ServiceName = "SpecterAgent";
});

builder.Services.AddHttpClient();
builder.Services.AddSingleton<EnrollmentService>();
builder.Services.AddHostedService<HeartbeatService>();
builder.Services.AddHostedService<EventMonitorService>();
builder.Services.AddSingleton<TelemetryUploader>();

var host = builder.Build();
host.Run();
