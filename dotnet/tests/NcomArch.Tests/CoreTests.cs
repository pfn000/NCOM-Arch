using NcomArch.Interop;
using Xunit;

namespace NcomArch.Tests;

/// <summary>.NET -> ncom_arch.dll (Rust core) over P/Invoke.</summary>
public class CoreTests
{
    private static readonly NcomRect G0 = new(95, 64, 410, 232);

    [Fact]
    public void NativeVersionAndAbi()
    {
        Assert.Equal("0.1.0", NcomCore.NativeVersion);
        Assert.Equal(1u, NcomCore.AbiVersion);
    }

    [Fact]
    public void HelloReportsProtocolAndAnatomy()
    {
        using var core = new NcomCore();
        var hello = core.Hello();
        Assert.Equal(1, hello["protocol"]!.GetValue<int>());
        Assert.Equal(24.0, hello["anatomy"]!["corner_radius"]!.GetValue<double>());
    }

    [Fact]
    public void MaximizeFillsWorkAreaAndRestoreReturns()
    {
        using var core = new NcomCore();
        var id = core.Open("Notes", G0);
        var ev = core.Maximize(id);
        Assert.Equal("maximized", ev[0].Kind);
        Assert.Equal(new NcomRect(8, 48, 584, 276), core.WindowRect(id));
        core.Restore(id);
        Assert.Equal(G0, core.WindowRect(id));
    }

    [Fact]
    public void PillGesturesThroughPointerEvents()
    {
        using var core = new NcomCore();
        var id = core.Open("Notes", G0);
        // tap the pill -> info / properties
        core.Pointer(PointerKind.Down, 451, 71, 0);
        var tap = core.Pointer(PointerKind.Up, 451, 71, 80);
        Assert.Equal("info_requested", Assert.Single(tap).Kind);
        // swipe it down -> minimize
        core.Pointer(PointerKind.Down, 451, 71, 200);
        var swipe = core.Pointer(PointerKind.Up, 451, 101, 320);
        Assert.Equal("minimized", swipe[0].Kind);
        Assert.Equal(id, swipe[0].WindowId);
    }

    [Fact]
    public void ArcFlickCloses()
    {
        using var core = new NcomCore();
        var id = core.Open("Notes", G0);
        core.Pointer(PointerKind.Down, 493, 76, 0);
        core.Pointer(PointerKind.Move, 487, 82, 40);
        var ev = core.Pointer(PointerKind.Up, 479, 90, 80);
        Assert.Contains(ev, e => e.Kind == "closed" && e.WindowId == id);
        Assert.Empty(core.Windows());
    }

    [Fact]
    public void HitTestUsesTheSpec()
    {
        using var core = new NcomCore();
        var id = core.Open("Notes", G0);
        Assert.Equal((id, WindowPart.Pill), core.HitTest(451, 71));
        Assert.Equal((id, WindowPart.Dots), core.HitTest(300, 71));
        Assert.Equal((id, WindowPart.CornerArc), core.HitTest(493, 76));
        Assert.Equal((id, WindowPart.ResizeCorner), core.HitTest(496, 287));
        Assert.Null(core.HitTest(5, 5));
    }

    [Fact]
    public void PropertiesAndMenu()
    {
        using var core = new NcomCore();
        var id = core.Open("Plan", G0, app: "Notes");
        Assert.Equal("Notes", core.Properties(id)["hero"]!.GetValue<string>());
        var menu = core.Menu(id);
        Assert.Equal("File", menu["top_row"]![0]!.GetValue<string>());
        var labels = menu["groups"]!.AsArray().SelectMany(g => g!["items"]!.AsArray()).Select(i => i!["label"]!.GetValue<string>()).ToList();
        Assert.DoesNotContain(labels, l => l.Contains("Minimize") || l.Contains("Maximize"));
    }

    [Fact]
    public void ErrorsBecomeExceptions()
    {
        using var core = new NcomCore();
        var ex = Assert.Throws<NcomException>(() => core.Maximize(42));
        Assert.Contains("no window", ex.Message);
    }
}

public class PipeTests
{
    [Fact]
    public async Task PipeServerRoundTrip()
    {
        using var core = new NcomCore();
        var name = "ncom-arch-test-" + Guid.NewGuid().ToString("N")[..8];
        using var cts = new CancellationTokenSource();
        var server = new NcomPipeServer(core, name).RunAsync(cts.Token);
        using (var client = new NcomPipeClient(name))
        {
            var hello = await client.SendAsync("""{"cmd":"hello"}""");
            Assert.StartsWith("""{"ok":true""", hello);
            var open = await client.SendAsync("""{"cmd":"open","title":"Notes"}""");
            Assert.Contains("\"id\":1", open);
        }
        cts.Cancel();
        await server.WaitAsync(TimeSpan.FromSeconds(10));
    }
}

public class DriverContractTests
{
    [Fact]
    public void IoctlCodesMatchPublicH()
    {
        // CTL_CODE(FILE_DEVICE_UNKNOWN, 0x800.., METHOD_BUFFERED, FILE_ANY_ACCESS)
        Assert.Equal(0x222000u, NcomDriver.IoctlGetVersion);
        Assert.Equal(0x222004u, NcomDriver.IoctlSubmitInput);
        Assert.Equal(0x222008u, NcomDriver.IoctlWaitInput);
    }

    [Fact]
    public void PointerSampleLayoutRoundTrips()
    {
        var b = NcomDriver.EncodeSample(PointerKind.Move, -12, 345, 9_876_543_210UL);
        Assert.Equal(24, b.Length);
        Assert.Equal((PointerKind.Move, -12, 345, 9_876_543_210UL), NcomDriver.DecodeSample(b));
    }
}
