using System.IO.Pipes;
using System.Text;

namespace NcomArch.Interop;

/// <summary>
/// Serves the NCOM Arch JSON-lines protocol on a named pipe (\\.\pipe\ncom-arch on Windows;
/// .NET maps the same name to a Unix socket elsewhere). Every client shares one desktop.
/// </summary>
public sealed class NcomPipeServer(NcomCore core, string pipeName = NcomPipeServer.DefaultPipeName)
{
    public const string DefaultPipeName = "ncom-arch";
    public string PipeName { get; } = pipeName;

    public async Task RunAsync(CancellationToken ct)
    {
        var clients = new List<Task>();
        while (!ct.IsCancellationRequested)
        {
            var server = new NamedPipeServerStream(PipeName, PipeDirection.InOut,
                NamedPipeServerStream.MaxAllowedServerInstances, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
            try
            {
                await server.WaitForConnectionAsync(ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                await server.DisposeAsync().ConfigureAwait(false);
                break;
            }
            clients.Add(ServeClientAsync(server, ct));
            clients.RemoveAll(t => t.IsCompleted);
        }
        try { await Task.WhenAll(clients).ConfigureAwait(false); } catch (OperationCanceledException) { }
    }

    private async Task ServeClientAsync(NamedPipeServerStream pipe, CancellationToken ct)
    {
        await using (pipe)
        {
            using var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 4096, leaveOpen: true);
            await using var writer = new StreamWriter(pipe, new UTF8Encoding(false), 4096, leaveOpen: true) { AutoFlush = true, NewLine = "\n" };
            try
            {
                while (!ct.IsCancellationRequested && pipe.IsConnected)
                {
                    var line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
                    if (line is null) break;
                    if (line.Trim().Length == 0) continue;
                    await writer.WriteLineAsync(core.CallJson(line)).ConfigureAwait(false);
                }
            }
            catch (IOException) { /* client went away */ }
            catch (OperationCanceledException) { }
        }
    }
}

/// <summary>Client for <see cref="NcomPipeServer"/>.</summary>
public sealed class NcomPipeClient : IDisposable
{
    private readonly NamedPipeClientStream _pipe;
    private readonly StreamReader _reader;
    private readonly StreamWriter _writer;

    public NcomPipeClient(string pipeName = NcomPipeServer.DefaultPipeName, int timeoutMs = 5000)
    {
        _pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
        _pipe.Connect(timeoutMs);
        _reader = new StreamReader(_pipe, new UTF8Encoding(false), false, 4096, leaveOpen: true);
        _writer = new StreamWriter(_pipe, new UTF8Encoding(false), 4096, leaveOpen: true) { AutoFlush = true, NewLine = "\n" };
    }

    public async Task<string> SendAsync(string requestJson, CancellationToken ct = default)
    {
        await _writer.WriteLineAsync(requestJson.AsMemory(), ct).ConfigureAwait(false);
        return await _reader.ReadLineAsync(ct).ConfigureAwait(false) ?? throw new IOException("pipe closed");
    }

    public void Dispose()
    {
        _writer.Dispose();
        _reader.Dispose();
        _pipe.Dispose();
    }
}
