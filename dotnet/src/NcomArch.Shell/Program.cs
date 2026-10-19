using NcomArch.Interop;
using NcomArch.Shell;

// Install as a service (elevated):
//   sc.exe create NcomArchShell binPath= "C:\Program Files\NCOM Arch\NcomArch.Shell.exe" start= auto
var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddWindowsService(o => o.ServiceName = "NCOM Arch Shell");
builder.Services.AddSingleton(_ =>
{
    var width = builder.Configuration.GetValue("Desktop:Width", 0.0);
    var height = builder.Configuration.GetValue("Desktop:Height", 0.0);
    return new NcomCore(width, height);
});
builder.Services.AddHostedService<ShellWorker>();
builder.Build().Run();
