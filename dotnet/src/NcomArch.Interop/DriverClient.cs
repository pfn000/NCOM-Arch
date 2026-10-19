using System.Buffers.Binary;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Microsoft.Win32.SafeHandles;

namespace NcomArch.Interop;

/// <summary>
/// User-mode side of the NcomArchKm KMDF driver (windows/driver/NcomArchKm). The IOCTL codes
/// and struct layouts mirror windows/driver/NcomArchKm/Public.h.
/// </summary>
public static class NcomDriver
{
    public const string DevicePath = @"\\.\NcomArchKm";
    public const uint FileDeviceUnknown = 0x22;
    public const uint MethodBuffered = 0;
    public const uint FileAnyAccess = 0;

    public static uint CtlCode(uint deviceType, uint function, uint method, uint access) =>
        (deviceType << 16) | (access << 14) | (function << 2) | method;

    public static readonly uint IoctlGetVersion = CtlCode(FileDeviceUnknown, 0x800, MethodBuffered, FileAnyAccess);
    public static readonly uint IoctlSubmitInput = CtlCode(FileDeviceUnknown, 0x801, MethodBuffered, FileAnyAccess);
    public static readonly uint IoctlWaitInput = CtlCode(FileDeviceUnknown, 0x802, MethodBuffered, FileAnyAccess);

    /// <summary>NCOM_POINTER_SAMPLE: ULONG Kind, LONG X, LONG Y, ULONG Reserved, ULONGLONG TimeMs (24 bytes).</summary>
    public const int PointerSampleSize = 24;

    public static byte[] EncodeSample(PointerKind kind, int x, int y, ulong timeMs)
    {
        var b = new byte[PointerSampleSize];
        BinaryPrimitives.WriteUInt32LittleEndian(b.AsSpan(0), (uint)kind);
        BinaryPrimitives.WriteInt32LittleEndian(b.AsSpan(4), x);
        BinaryPrimitives.WriteInt32LittleEndian(b.AsSpan(8), y);
        BinaryPrimitives.WriteUInt64LittleEndian(b.AsSpan(16), timeMs);
        return b;
    }

    public static (PointerKind Kind, int X, int Y, ulong TimeMs) DecodeSample(ReadOnlySpan<byte> b) =>
        ((PointerKind)BinaryPrimitives.ReadUInt32LittleEndian(b),
         BinaryPrimitives.ReadInt32LittleEndian(b[4..]),
         BinaryPrimitives.ReadInt32LittleEndian(b[8..]),
         BinaryPrimitives.ReadUInt64LittleEndian(b[16..]));
}

/// <summary>Open handle to the installed driver. Windows only; the driver must be installed (test-signed).</summary>
[SupportedOSPlatform("windows")]
public sealed class DriverClient : IDisposable
{
    private readonly SafeFileHandle _h;

    private DriverClient(SafeFileHandle h) => _h = h;

    /// <summary>Null when the driver isn't installed.</summary>
    public static DriverClient? TryOpen()
    {
        var h = CreateFileW(NcomDriver.DevicePath, 0xC0000000 /* GENERIC_READ|WRITE */, 0, IntPtr.Zero, 3 /* OPEN_EXISTING */, 0, IntPtr.Zero);
        if (h.IsInvalid) { h.Dispose(); return null; }
        return new DriverClient(h);
    }

    public (uint Major, uint Minor, uint Patch, uint Abi) GetVersion()
    {
        var o = new byte[16];
        Ioctl(NcomDriver.IoctlGetVersion, Array.Empty<byte>(), o);
        return (BitConverter.ToUInt32(o, 0), BitConverter.ToUInt32(o, 4), BitConverter.ToUInt32(o, 8), BitConverter.ToUInt32(o, 12));
    }

    public void Submit(PointerKind kind, int x, int y, ulong timeMs) =>
        Ioctl(NcomDriver.IoctlSubmitInput, NcomDriver.EncodeSample(kind, x, y, timeMs), Array.Empty<byte>());

    /// <summary>Blocks until the driver has a pointer sample (inverted call).</summary>
    public (PointerKind Kind, int X, int Y, ulong TimeMs) WaitInput()
    {
        var o = new byte[NcomDriver.PointerSampleSize];
        Ioctl(NcomDriver.IoctlWaitInput, Array.Empty<byte>(), o);
        return NcomDriver.DecodeSample(o);
    }

    private void Ioctl(uint code, byte[] input, byte[] output)
    {
        if (!DeviceIoControl(_h, code, input, input.Length, output, output.Length, out _, IntPtr.Zero))
            throw new Win32Exception(Marshal.GetLastWin32Error());
    }

    public void Dispose() => _h.Dispose();

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr security, uint disposition, uint flags, IntPtr template);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool DeviceIoControl(SafeFileHandle device, uint code, byte[] inBuf, int inLen, byte[] outBuf, int outLen, out int returned, IntPtr overlapped);
}
