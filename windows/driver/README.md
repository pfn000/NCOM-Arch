# NcomArchKm: NCOM Arch kernel input broker (KMDF)

A root-enumerated KMDF software device (`Root\NcomArchKm`) that brokers pointer samples to the NCOM Arch shell. The shell (`NcomArch.Shell`) opens `\\.\NcomArchKm` through `NcomArch.Interop.DriverClient`.

| IOCTL | Code | What it does |
|---|---|---|
| `IOCTL_NCOM_GET_VERSION` | `0x222000` | driver version and ABI |
| `IOCTL_NCOM_SUBMIT_INPUT` | `0x222004` | queue one `NCOM_POINTER_SAMPLE` (24 bytes: kind, x, y, reserved, time ms) |
| `IOCTL_NCOM_WAIT_INPUT` | `0x222008` | pends until a sample is available (inverted call) |

Samples wait in a 256-entry ring; the oldest is dropped when it is full.

## Status, honestly

- **Skeleton.** It compiles with the WDK (`/W4 /WX`), stampinf fills the INF, Inf2Cat makes the catalog and CI test-signs `.sys` + `.cat` with a throwaway self-signed certificate. It has **not** been loaded on a real machine yet.
- Samples come from user mode today. Reading the touchpad/touchscreen directly needs a HID (precision touchpad) **filter** driver underneath. That is the next kernel piece and isn't written.

## Build

Visual Studio 2022 + the Windows Driver Kit (WDK), x64:

```
msbuild windows\driver\NcomArchKm\NcomArchKm.vcxproj /p:Configuration=Release /p:Platform=x64
```

## Signing

- **Test signing (what CI does):** a self-signed certificate. Loads only on a machine in test mode: `bcdedit /set testsigning on`, reboot, trust the `.cer`, then `pnputil /add-driver NcomArchKm.inf /install` and `devcon install NcomArchKm.inf Root\NcomArchKm`.
- **Production:** Windows 10/11 only loads kernel drivers signed by Microsoft. That needs Saidie's **EV code-signing certificate**, a **Partner Center (Hardware Dev Center)** account, and the package submitted for **attestation signing** (or WHQL). Nothing in this repo can do that step for her.
