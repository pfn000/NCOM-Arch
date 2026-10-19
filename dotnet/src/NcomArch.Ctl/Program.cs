using NcomArch.Interop;

// ncomctl [--pipe NAME | --inproc] (demo | <json request>)...
//   ncomctl --inproc demo
//   ncomctl '{"cmd":"hello"}' '{"cmd":"list"}'
string pipe = NcomPipeServer.DefaultPipeName;
bool inproc = false;
var requests = new List<string>();
for (int i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--pipe": pipe = args[++i]; break;
        case "--inproc": inproc = true; break;
        case "--version": Console.WriteLine($"ncomctl 0.1.0, core {NcomCore.NativeVersion}"); return 0;
        default: requests.Add(args[i]); break;
    }
}
if (requests.Count == 0)
{
    Console.Error.WriteLine("usage: ncomctl [--pipe NAME | --inproc] (demo | <json request>)...");
    return 2;
}
if (requests is ["demo"])
    requests = Demo.Requests;

Func<string, string> send;
NcomCore? core = null;
NcomPipeClient? client = null;
if (inproc)
{
    core = new NcomCore();
    send = core.CallJson;
}
else
{
    client = new NcomPipeClient(pipe);
    send = r => client.SendAsync(r).GetAwaiter().GetResult();
}
int failures = 0;
foreach (var r in requests)
{
    var resp = send(r);
    Console.WriteLine($"-> {r}");
    Console.WriteLine($"<- {resp}");
    if (!resp.StartsWith("{\"ok\":true", StringComparison.Ordinal)) failures++;
}
core?.Dispose();
client?.Dispose();
return failures == 0 ? 0 : 1;

static class Demo
{
    // Open a window, swipe its pill up (maximize) and back down (restore), tap the pill for Properties.
    public static List<string> Requests =>
    [
        """{"cmd":"hello"}""",
        """{"cmd":"open","title":"Plan","app":"Notes","rect":{"x":95,"y":64,"w":410,"h":232},"document":{"name":"Plan.ncom","path":"C:\\Users\\Saidie\\Documents\\Plan.ncom","size_bytes":248832,"kind":"NCOM document"}}""",
        """{"cmd":"pointer","kind":"down","x":451,"y":71,"t_ms":0}""",
        """{"cmd":"pointer","kind":"up","x":451,"y":41,"t_ms":120}""",
        """{"cmd":"tick","t_ms":420}""",
        """{"cmd":"pointer","kind":"down","x":538,"y":55,"t_ms":1000}""",
        """{"cmd":"pointer","kind":"up","x":538,"y":85,"t_ms":1120}""",
        """{"cmd":"pointer","kind":"down","x":451,"y":71,"t_ms":2000}""",
        """{"cmd":"pointer","kind":"up","x":451,"y":71,"t_ms":2080}""",
        """{"cmd":"properties","id":1}""",
        """{"cmd":"list"}""",
    ];
}
