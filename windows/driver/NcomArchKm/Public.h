/*
 * Public.h - contract between the NcomArchKm KMDF driver and user mode
 * (NcomArch.Interop.DriverClient in dotnet/src/NcomArch.Interop/DriverClient.cs mirrors it).
 */
#pragma once

/* {5B1F6A3C-2D4E-4C1A-9E7B-3A510C8D6F21} */
DEFINE_GUID(GUID_DEVINTERFACE_NCOM_ARCH,
    0x5b1f6a3c, 0x2d4e, 0x4c1a, 0x9e, 0x7b, 0x3a, 0x51, 0x0c, 0x8d, 0x6f, 0x21);

#define NCOM_DOS_DEVICE_NAME L"\\DosDevices\\NcomArchKm"   /* user mode: \\.\NcomArchKm */

#define NCOM_DRIVER_VERSION_MAJOR 0
#define NCOM_DRIVER_VERSION_MINOR 1
#define NCOM_DRIVER_VERSION_PATCH 0
#define NCOM_DRIVER_ABI           1

#define IOCTL_NCOM_GET_VERSION   CTL_CODE(FILE_DEVICE_UNKNOWN, 0x800, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_NCOM_SUBMIT_INPUT  CTL_CODE(FILE_DEVICE_UNKNOWN, 0x801, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_NCOM_WAIT_INPUT    CTL_CODE(FILE_DEVICE_UNKNOWN, 0x802, METHOD_BUFFERED, FILE_ANY_ACCESS)

/* Pointer kinds: same order as the core's PointerKind (down, move, up, cancel). */
#define NCOM_POINTER_DOWN    0u
#define NCOM_POINTER_MOVE    1u
#define NCOM_POINTER_UP      2u
#define NCOM_POINTER_CANCEL  3u

typedef struct _NCOM_VERSION_INFO {
    ULONG Major;
    ULONG Minor;
    ULONG Patch;
    ULONG Abi;
} NCOM_VERSION_INFO, *PNCOM_VERSION_INFO;

typedef struct _NCOM_POINTER_SAMPLE {
    ULONG     Kind;      /* NCOM_POINTER_* */
    LONG      X;         /* desktop pixels */
    LONG      Y;
    ULONG     Reserved;  /* must be 0 */
    ULONGLONG TimeMs;
} NCOM_POINTER_SAMPLE, *PNCOM_POINTER_SAMPLE;

C_ASSERT(sizeof(NCOM_VERSION_INFO) == 16);
C_ASSERT(sizeof(NCOM_POINTER_SAMPLE) == 24);
