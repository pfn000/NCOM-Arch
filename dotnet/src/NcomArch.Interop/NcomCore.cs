using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace NcomArch.Interop;

public enum WindowPart : uint { Content = 0, CornerArc = 1, Pill = 2, Dots = 3, ResizeCorner = 4 }

public enum PointerKind { Down, Move, Up, Cancel }

public enum SnapZone { Full, Left, Right }

public sealed record NcomRect(double X, double Y, double W, double H);

/// <summary>One event from the window system, e.g. {"event":"minimized","id":1}.</summary>
public sealed record NcomEvent(string Kind, uint? WindowId, JsonObject Raw);

public sealed class NcomException(string message) : Exception(message);

/// <summary>
/// The NCOM Arch window system, running in-process inside the Rust core (ncom_arch.dll).
/// Thread-safe: calls are serialized.
/// </summary>
public sealed class NcomCore : IDisposable
{
    private readonly NcomSessionHandle _session;
    private readonly object _gate = new();

    /// <param name="width">Desktop width; 0 = the 600 x 375 default.</param>
    public NcomCore(double width = 0, double height = 0)
    {
        _session = NativeMethods.ncom_session_new(width, height);
        if (_session.IsInvalid) throw new NcomException("ncom_session_new returned NULL");
    }

    public static string NativeVersion => Marshal.PtrToStringUTF8(NativeMethods.ncom_version()) ?? "";
    public static uint AbiVersion => NativeMethods.ncom_abi_version();

    /// <summary>Raw protocol call: one JSON request in, one JSON response out.</summary>
    public string CallJson(string requestJson)
    {
        var bytes = Encoding.UTF8.GetBytes(requestJson + "\0");
        lock (_gate)
        {
            ObjectDisposedException.ThrowIf(_session.IsClosed, this);
            IntPtr p = NativeMethods.ncom_session_call(_session, bytes);
            if (p == IntPtr.Zero) throw new NcomException("ncom_session_call returned NULL");
            try { return Marshal.PtrToStringUTF8(p) ?? ""; }
            finally { NativeMethods.ncom_string_free(p); }
        }
    }

    /// <summary>Send a request object; throws <see cref="NcomException"/> on {"ok":false}.</summary>
    public JsonObject Call(object request)
    {
        var resp = JsonNode.Parse(CallJson(JsonSerializer.Serialize(request)))!.AsObject();
        if (resp["ok"]?.GetValue<bool>() != true)
            throw new NcomException(resp["error"]?.GetValue<string>() ?? "unknown error");
        return resp;
    }

    public static IReadOnlyList<NcomEvent> Events(JsonObject response)
    {
        var list = new List<NcomEvent>();
        if (response["events"] is JsonArray arr)
            foreach (var e in arr)
                if (e is JsonObject o)
                    list.Add(new NcomEvent(o["event"]?.GetValue<string>() ?? "", o["id"]?.GetValue<uint>(), o));
        return list;
    }

    public JsonObject Hello() => (JsonObject)Call(new { cmd = "hello" })["result"]!;

    public uint Open(string title, NcomRect? rect = null, string? app = null, bool resizable = true)
    {
        object req = rect is null
            ? (object)new { cmd = "open", title, app, resizable }
            : (object)new { cmd = "open", title, app, resizable, rect = new { x = rect.X, y = rect.Y, w = rect.W, h = rect.H } };
        return Call(req)["result"]!["id"]!.GetValue<uint>();
    }

    public IReadOnlyList<NcomEvent> Close(uint id) => Events(Call(new { cmd = "close", id }));
    public IReadOnlyList<NcomEvent> Minimize(uint id) => Events(Call(new { cmd = "minimize", id }));
    public IReadOnlyList<NcomEvent> Maximize(uint id) => Events(Call(new { cmd = "maximize", id }));
    public IReadOnlyList<NcomEvent> Restore(uint id) => Events(Call(new { cmd = "restore", id }));
    public IReadOnlyList<NcomEvent> Snap(uint id, SnapZone zone) => Events(Call(new { cmd = "snap", id, zone = zone.ToString().ToLowerInvariant() }));

    public IReadOnlyList<NcomEvent> Pointer(PointerKind kind, double x, double y, double tMs) =>
        Events(Call(new { cmd = "pointer", kind = kind.ToString().ToLowerInvariant(), x, y, t_ms = tMs }));

    public IReadOnlyList<NcomEvent> Tick(double tMs) => Events(Call(new { cmd = "tick", t_ms = tMs }));

    public JsonArray Windows() => (JsonArray)Call(new { cmd = "list" })["result"]!["windows"]!;

    public NcomRect WindowRect(uint id)
    {
        foreach (var w in Windows())
            if (w!["id"]!.GetValue<uint>() == id)
            {
                var r = w["rect"]!;
                return new NcomRect(r["x"]!.GetValue<double>(), r["y"]!.GetValue<double>(), r["w"]!.GetValue<double>(), r["h"]!.GetValue<double>());
            }
        throw new NcomException($"no window with id {id}");
    }

    public JsonObject Properties(uint id) => (JsonObject)Call(new { cmd = "properties", id })["result"]!;
    public JsonObject Menu(uint id) => (JsonObject)Call(new { cmd = "menu", id })["result"]!;

    /// <summary>Hit test through the plain C entry point (no JSON).</summary>
    public (uint Id, WindowPart Part)? HitTest(double x, double y)
    {
        lock (_gate)
        {
            return NativeMethods.ncom_hit_test(_session, x, y, out var id, out var part) == 1 ? (id, (WindowPart)part) : null;
        }
    }

    public void Dispose()
    {
        lock (_gate) _session.Dispose();
    }
}
