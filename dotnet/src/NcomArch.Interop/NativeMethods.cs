using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace NcomArch.Interop;

/// <summary>P/Invoke surface of ncom_arch.dll (crates/ncom-ffi, header crates/ncom-ffi/include/ncom_arch.h).</summary>
internal static class NativeMethods
{
    internal const string Lib = "ncom_arch";

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern IntPtr ncom_version();

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern uint ncom_abi_version();

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern NcomSessionHandle ncom_session_new(double width, double height);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern void ncom_session_free(IntPtr session);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern IntPtr ncom_session_call(NcomSessionHandle session, byte[] requestUtf8);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern int ncom_hit_test(NcomSessionHandle session, double x, double y, out uint id, out uint part);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    internal static extern void ncom_string_free(IntPtr s);
}

/// <summary>Owns one native session; freed with ncom_session_free.</summary>
public sealed class NcomSessionHandle : SafeHandleZeroOrMinusOneIsInvalid
{
    public NcomSessionHandle() : base(true) { }

    protected override bool ReleaseHandle()
    {
        NativeMethods.ncom_session_free(handle);
        return true;
    }
}
