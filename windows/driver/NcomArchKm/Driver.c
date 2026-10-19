/*
 * NcomArchKm.sys - NCOM Arch kernel input broker (KMDF skeleton).
 *
 * A root-enumerated software device that brokers pointer samples to the NCOM Arch shell:
 *   IOCTL_NCOM_SUBMIT_INPUT  queue one NCOM_POINTER_SAMPLE (today: from user mode; later: from
 *                            a HID / precision-touchpad filter attached below this driver)
 *   IOCTL_NCOM_WAIT_INPUT    "inverted call": pends until a sample is available, then completes
 *   IOCTL_NCOM_GET_VERSION   driver version + ABI
 * Samples wait in a 256-entry ring (oldest dropped when full). The default queue is sequential,
 * so SUBMIT and WAIT never race; the spinlock guards the ring for future parallel paths.
 *
 * STATUS: skeleton. It builds, stamps and test-signs in CI; it has not been loaded on a machine yet.
 */
#include <ntddk.h>
#include <wdf.h>
#include <initguid.h>
#include "Public.h"

#define NCOM_RING_CAPACITY 256

typedef struct _NCOM_DEVICE_CONTEXT {
    WDFSPINLOCK Lock;
    WDFQUEUE PendingWaits;
    ULONG Head;
    ULONG Count;
    ULONGLONG Dropped;
    NCOM_POINTER_SAMPLE Ring[NCOM_RING_CAPACITY];
} NCOM_DEVICE_CONTEXT, *PNCOM_DEVICE_CONTEXT;

WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(NCOM_DEVICE_CONTEXT, NcomGetContext)

DRIVER_INITIALIZE DriverEntry;
EVT_WDF_DRIVER_DEVICE_ADD NcomEvtDeviceAdd;
EVT_WDF_IO_QUEUE_IO_DEVICE_CONTROL NcomEvtIoDeviceControl;

#ifdef ALLOC_PRAGMA
#pragma alloc_text(INIT, DriverEntry)
#pragma alloc_text(PAGE, NcomEvtDeviceAdd)
#endif

static VOID
NcomRingPush(_In_ PNCOM_DEVICE_CONTEXT Ctx, _In_ const NCOM_POINTER_SAMPLE* Sample)
{
    ULONG tail;

    WdfSpinLockAcquire(Ctx->Lock);
    if (Ctx->Count == NCOM_RING_CAPACITY) {
        Ctx->Head = (Ctx->Head + 1) % NCOM_RING_CAPACITY;
        Ctx->Count--;
        Ctx->Dropped++;
    }
    tail = (Ctx->Head + Ctx->Count) % NCOM_RING_CAPACITY;
    Ctx->Ring[tail] = *Sample;
    Ctx->Count++;
    WdfSpinLockRelease(Ctx->Lock);
}

static BOOLEAN
NcomRingPop(_In_ PNCOM_DEVICE_CONTEXT Ctx, _Out_ PNCOM_POINTER_SAMPLE Out)
{
    BOOLEAN have = FALSE;

    RtlZeroMemory(Out, sizeof(*Out));
    WdfSpinLockAcquire(Ctx->Lock);
    if (Ctx->Count > 0) {
        *Out = Ctx->Ring[Ctx->Head];
        Ctx->Head = (Ctx->Head + 1) % NCOM_RING_CAPACITY;
        Ctx->Count--;
        have = TRUE;
    }
    WdfSpinLockRelease(Ctx->Lock);
    return have;
}

NTSTATUS
DriverEntry(_In_ PDRIVER_OBJECT DriverObject, _In_ PUNICODE_STRING RegistryPath)
{
    WDF_DRIVER_CONFIG config;

    WDF_DRIVER_CONFIG_INIT(&config, NcomEvtDeviceAdd);
    return WdfDriverCreate(DriverObject, RegistryPath, WDF_NO_OBJECT_ATTRIBUTES, &config, WDF_NO_HANDLE);
}

NTSTATUS
NcomEvtDeviceAdd(_In_ WDFDRIVER Driver, _Inout_ PWDFDEVICE_INIT DeviceInit)
{
    NTSTATUS status;
    WDFDEVICE device;
    WDF_OBJECT_ATTRIBUTES attributes;
    WDF_IO_QUEUE_CONFIG queueConfig;
    PNCOM_DEVICE_CONTEXT ctx;
    DECLARE_CONST_UNICODE_STRING(symbolicLink, NCOM_DOS_DEVICE_NAME);

    UNREFERENCED_PARAMETER(Driver);
    PAGED_CODE();

    WDF_OBJECT_ATTRIBUTES_INIT_CONTEXT_TYPE(&attributes, NCOM_DEVICE_CONTEXT);
    status = WdfDeviceCreate(&DeviceInit, &attributes, &device);
    if (!NT_SUCCESS(status)) {
        return status;
    }
    ctx = NcomGetContext(device);

    WDF_OBJECT_ATTRIBUTES_INIT(&attributes);
    attributes.ParentObject = device;
    status = WdfSpinLockCreate(&attributes, &ctx->Lock);
    if (!NT_SUCCESS(status)) {
        return status;
    }

    status = WdfDeviceCreateDeviceInterface(device, &GUID_DEVINTERFACE_NCOM_ARCH, NULL);
    if (!NT_SUCCESS(status)) {
        return status;
    }
    status = WdfDeviceCreateSymbolicLink(device, &symbolicLink);
    if (!NT_SUCCESS(status)) {
        return status;
    }

    WDF_IO_QUEUE_CONFIG_INIT_DEFAULT_QUEUE(&queueConfig, WdfIoQueueDispatchSequential);
    queueConfig.EvtIoDeviceControl = NcomEvtIoDeviceControl;
    status = WdfIoQueueCreate(device, &queueConfig, WDF_NO_OBJECT_ATTRIBUTES, WDF_NO_HANDLE);
    if (!NT_SUCCESS(status)) {
        return status;
    }

    /* Readers parked here until a sample arrives (inverted call). */
    WDF_IO_QUEUE_CONFIG_INIT(&queueConfig, WdfIoQueueDispatchManual);
    return WdfIoQueueCreate(device, &queueConfig, WDF_NO_OBJECT_ATTRIBUTES, &ctx->PendingWaits);
}

VOID
NcomEvtIoDeviceControl(
    _In_ WDFQUEUE Queue,
    _In_ WDFREQUEST Request,
    _In_ size_t OutputBufferLength,
    _In_ size_t InputBufferLength,
    _In_ ULONG IoControlCode)
{
    PNCOM_DEVICE_CONTEXT ctx = NcomGetContext(WdfIoQueueGetDevice(Queue));
    NTSTATUS status = STATUS_INVALID_DEVICE_REQUEST;
    ULONG_PTR info = 0;
    PVOID buffer = NULL;
    NCOM_POINTER_SAMPLE sample;
    WDFREQUEST waiter = NULL;

    RtlZeroMemory(&sample, sizeof(sample));

    UNREFERENCED_PARAMETER(OutputBufferLength);
    UNREFERENCED_PARAMETER(InputBufferLength);

    switch (IoControlCode) {
    case IOCTL_NCOM_GET_VERSION:
        status = WdfRequestRetrieveOutputBuffer(Request, sizeof(NCOM_VERSION_INFO), &buffer, NULL);
        if (NT_SUCCESS(status)) {
            PNCOM_VERSION_INFO v = (PNCOM_VERSION_INFO)buffer;
            v->Major = NCOM_DRIVER_VERSION_MAJOR;
            v->Minor = NCOM_DRIVER_VERSION_MINOR;
            v->Patch = NCOM_DRIVER_VERSION_PATCH;
            v->Abi = NCOM_DRIVER_ABI;
            info = sizeof(NCOM_VERSION_INFO);
        }
        break;

    case IOCTL_NCOM_SUBMIT_INPUT:
        status = WdfRequestRetrieveInputBuffer(Request, sizeof(NCOM_POINTER_SAMPLE), &buffer, NULL);
        if (!NT_SUCCESS(status)) {
            break;
        }
        sample = *(PNCOM_POINTER_SAMPLE)buffer;
        if (sample.Kind > NCOM_POINTER_CANCEL || sample.Reserved != 0) {
            status = STATUS_INVALID_PARAMETER;
            break;
        }
        /* Hand it straight to a parked reader, else keep it in the ring. */
        if (NT_SUCCESS(WdfIoQueueRetrieveNextRequest(ctx->PendingWaits, &waiter))) {
            PVOID out = NULL;
            NTSTATUS ws = WdfRequestRetrieveOutputBuffer(waiter, sizeof(NCOM_POINTER_SAMPLE), &out, NULL);
            if (NT_SUCCESS(ws)) {
                *(PNCOM_POINTER_SAMPLE)out = sample;
                WdfRequestCompleteWithInformation(waiter, STATUS_SUCCESS, sizeof(NCOM_POINTER_SAMPLE));
            } else {
                WdfRequestComplete(waiter, ws);
                NcomRingPush(ctx, &sample);
            }
        } else {
            NcomRingPush(ctx, &sample);
        }
        status = STATUS_SUCCESS;
        break;

    case IOCTL_NCOM_WAIT_INPUT:
        status = WdfRequestRetrieveOutputBuffer(Request, sizeof(NCOM_POINTER_SAMPLE), &buffer, NULL);
        if (!NT_SUCCESS(status)) {
            break;
        }
        if (NcomRingPop(ctx, (PNCOM_POINTER_SAMPLE)buffer)) {
            info = sizeof(NCOM_POINTER_SAMPLE);
            status = STATUS_SUCCESS;
            break;
        }
        status = WdfRequestForwardToIoQueue(Request, ctx->PendingWaits);
        if (NT_SUCCESS(status)) {
            return; /* completed later by a SUBMIT */
        }
        break;

    default:
        break;
    }

    WdfRequestCompleteWithInformation(Request, status, info);
}
