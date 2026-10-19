using NcomArch.Interop;

namespace NcomArch.Shell;

/// <summary>Serves the window system on the named pipe until the host stops.</summary>
public sealed class ShellWorker(NcomCore core, ILogger<ShellWorker> log, IConfiguration config) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var pipe = config.GetValue("Pipe:Name", NcomPipeServer.DefaultPipeName)!;
        log.LogInformation("NCOM Arch core {Version} (ABI {Abi}) serving on pipe {Pipe}",
            NcomCore.NativeVersion, NcomCore.AbiVersion, pipe);
        if (OperatingSystem.IsWindows())
        {
            using var driver = DriverClient.TryOpen();
            log.LogInformation(driver is null
                ? "NcomArchKm driver not installed: pointer input comes from clients only"
                : "NcomArchKm driver found");
        }
        await new NcomPipeServer(core, pipe).RunAsync(stoppingToken);
    }
}
