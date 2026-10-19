/*
 * ncom_arch.h - C ABI of the NCOM Arch core (ncom_arch.dll / libncom_arch.so).
 *
 * Every call speaks the JSON-lines protocol documented in crates/ncom-core/src/ipc.rs:
 *   {"cmd":"open","title":"Notes"}  ->  {"ok":true,"result":{"id":1},"events":[...]}
 * Strings returned by ncom_session_call must be released with ncom_string_free.
 * A session is not thread-safe: use it from one thread at a time.
 */
#ifndef NCOM_ARCH_H
#define NCOM_ARCH_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NCOM_ABI_VERSION 1

/* Part codes written by ncom_hit_test. */
#define NCOM_PART_CONTENT        0
#define NCOM_PART_CORNER_ARC     1
#define NCOM_PART_PILL           2
#define NCOM_PART_DOTS           3
#define NCOM_PART_RESIZE_CORNER  4

typedef struct NcomSession NcomSession;

const char*   ncom_version(void);                 /* static, do not free */
uint32_t      ncom_abi_version(void);
NcomSession*  ncom_session_new(double width, double height); /* 0, 0 = 600 x 375 default */
void          ncom_session_free(NcomSession* session);
char*         ncom_session_call(NcomSession* session, const char* request_json);
int32_t       ncom_hit_test(const NcomSession* session, double x, double y,
                            uint32_t* out_id, uint32_t* out_part);
void          ncom_string_free(char* s);

#ifdef __cplusplus
}
#endif

#endif /* NCOM_ARCH_H */
