/*
 * /usr/local/bin/exec-init  (compiled into mios-agent-sandbox image)
 *
 * In-container PID 1 wrapper per FS+OS Control guide §15.
 *
 * Behavior:
 *   1. Probe Landlock ABI at runtime (LANDLOCK_CREATE_RULESET_VERSION).
 *   2. Build a ruleset with the access masks available on this ABI.
 *   3. Allow /work + /tmp full rw; allow /usr /etc /lib /lib64 /bin /sbin
 *      /proc/self read-only.
 *   4. PR_SET_NO_NEW_PRIVS (mandatory before landlock_restrict_self).
 *   5. landlock_restrict_self -- everything spawned inherits this domain.
 *   6. Apply rlimits (RLIMIT_AS, RLIMIT_NPROC, RLIMIT_NOFILE).
 *   7. exec the caller's command. argv[1..] is the command.
 *
 * Fails CLOSED on every error path: if Landlock is unavailable or
 * any allow_path() fails, exit with status 2 instead of execing
 * an unconfined command. The container is the second line of
 * defense (seccomp + Network=none + DropCapability=ALL), so a
 * Landlock-only failure does not breach isolation; but failing
 * closed makes the contract obvious.
 *
 * ABI table the guide §4 enumerates:
 *   ABI 1 (5.13): fs read/write/exec/make/remove
 *   ABI 2 (5.19): LANDLOCK_ACCESS_FS_REFER
 *   ABI 3 (6.2):  LANDLOCK_ACCESS_FS_TRUNCATE
 *   ABI 4 (6.7):  TCP bind/connect rules
 *   ABI 5 (6.10): LANDLOCK_ACCESS_FS_IOCTL_DEV
 *   ABI 6 (6.12): scope_abstract_unix_socket + scope_signal
 *
 * Build:
 *   musl-gcc -static -Wall -Wextra -O2 -o exec-init exec-init.c
 */

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/landlock.h>
/* NOTE: do NOT include <linux/prctl.h> -- it redefines `struct prctl_mm_map`
 * already provided by <sys/prctl.h> below (build error on musl/alpine kernel
 * headers). <sys/prctl.h> supplies prctl() + the PR_* constants we use; any
 * constant a given libc omits is fallback-#define'd below. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef LANDLOCK_ACCESS_FS_REFER
#define LANDLOCK_ACCESS_FS_REFER (1ULL << 13)
#endif
#ifndef LANDLOCK_ACCESS_FS_TRUNCATE
#define LANDLOCK_ACCESS_FS_TRUNCATE (1ULL << 14)
#endif
#ifndef LANDLOCK_ACCESS_FS_IOCTL_DEV
#define LANDLOCK_ACCESS_FS_IOCTL_DEV (1ULL << 15)
#endif
#ifndef LANDLOCK_ACCESS_NET_BIND_TCP
#define LANDLOCK_ACCESS_NET_BIND_TCP (1ULL << 0)
#endif
#ifndef LANDLOCK_ACCESS_NET_CONNECT_TCP
#define LANDLOCK_ACCESS_NET_CONNECT_TCP (1ULL << 1)
#endif
#ifndef LANDLOCK_CREATE_RULESET_VERSION
#define LANDLOCK_CREATE_RULESET_VERSION (1U << 0)
#endif
/* PR_SET_NO_NEW_PRIVS comes from <sys/prctl.h>; fallback for an older libc. */
#ifndef PR_SET_NO_NEW_PRIVS
#define PR_SET_NO_NEW_PRIVS 38
#endif
/* Kernel headers older than the landlock-NET ABI (v4, Linux 6.7) define a
 * `struct landlock_ruleset_attr` WITHOUT `handled_access_net`, so referencing
 * that field fails to COMPILE on the alpine base even though we gate its USE on
 * the runtime ABI. Use our own complete struct (both fields, kernel-ABI order)
 * for the create call: the syscall is size-gated, and on a pre-v4 kernel we set
 * handled_access_net=0 (abi<4), so the kernel's forward-compat zero-check on the
 * trailing field passes. This compiles against ANY header + works on any kernel. */
struct mios_landlock_ruleset_attr {
    __u64 handled_access_fs;
    __u64 handled_access_net;
};

static int ll_create(const void *a, size_t s, __u32 f) {
    return (int)syscall(SYS_landlock_create_ruleset, a, s, f);
}
static int ll_addrule(int r, enum landlock_rule_type t, const void *a, __u32 f) {
    return (int)syscall(SYS_landlock_add_rule, r, t, a, f);
}
static int ll_restrict(int r, __u32 f) {
    return (int)syscall(SYS_landlock_restrict_self, r, f);
}

/* Allow a path subtree with the given access mask. Skips silently if
 * the path doesn't exist (containers vary in which dirs are present). */
static int allow_path(int rs, const char *p, __u64 access) {
    int fd = open(p, O_PATH | O_CLOEXEC);
    if (fd < 0) {
        if (errno == ENOENT) return 0;
        fprintf(stderr, "exec-init: open(%s, O_PATH): %s\n", p, strerror(errno));
        return -1;
    }
    struct landlock_path_beneath_attr pb = {
        .allowed_access = access,
        .parent_fd      = fd,
    };
    int rc = ll_addrule(rs, LANDLOCK_RULE_PATH_BENEATH, &pb, 0);
    close(fd);
    if (rc < 0) {
        fprintf(stderr, "exec-init: landlock_add_rule(%s): %s\n", p, strerror(errno));
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "exec-init: usage: exec-init <cmd> [args...]\n");
        return 2;
    }

    /* Probe ABI version. Returns the kernel-supported version or
     * negative on error. ABI < 1 means Landlock unavailable -> fail closed. */
    int abi = ll_create(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION);
    if (abi < 1) {
        fprintf(stderr, "exec-init: Landlock unavailable (rc=%d errno=%s) -- failing closed\n",
                abi, strerror(errno));
        return 2;
    }
    fprintf(stderr, "exec-init: Landlock ABI %d\n", abi);

    /* Build access masks. Each entry is only ORed in if the kernel
     * supports it (otherwise create_ruleset returns EINVAL). */
    __u64 fs_all =
        LANDLOCK_ACCESS_FS_EXECUTE      | LANDLOCK_ACCESS_FS_WRITE_FILE |
        LANDLOCK_ACCESS_FS_READ_FILE    | LANDLOCK_ACCESS_FS_READ_DIR   |
        LANDLOCK_ACCESS_FS_REMOVE_DIR   | LANDLOCK_ACCESS_FS_REMOVE_FILE |
        LANDLOCK_ACCESS_FS_MAKE_REG     | LANDLOCK_ACCESS_FS_MAKE_DIR   |
        LANDLOCK_ACCESS_FS_MAKE_SYM     | LANDLOCK_ACCESS_FS_MAKE_CHAR  |
        LANDLOCK_ACCESS_FS_MAKE_BLOCK   | LANDLOCK_ACCESS_FS_MAKE_SOCK  |
        LANDLOCK_ACCESS_FS_MAKE_FIFO;
    if (abi >= 2) fs_all |= LANDLOCK_ACCESS_FS_REFER;
    if (abi >= 3) fs_all |= LANDLOCK_ACCESS_FS_TRUNCATE;
    if (abi >= 5) fs_all |= LANDLOCK_ACCESS_FS_IOCTL_DEV;

    __u64 fs_ro = LANDLOCK_ACCESS_FS_EXECUTE | LANDLOCK_ACCESS_FS_READ_FILE |
                  LANDLOCK_ACCESS_FS_READ_DIR;

    struct mios_landlock_ruleset_attr attr = { .handled_access_fs = fs_all,
                                               .handled_access_net = 0 };
    /* ABI 4+: also handle TCP access. We add NO connect/bind rules
     * below, which means default-deny for both -- matching the
     * Quadlet's Network=none belt-and-braces. */
    if (abi >= 4) {
        attr.handled_access_net = LANDLOCK_ACCESS_NET_BIND_TCP |
                                  LANDLOCK_ACCESS_NET_CONNECT_TCP;
    }

    int rs = ll_create(&attr, sizeof(attr), 0);
    if (rs < 0) {
        fprintf(stderr, "exec-init: landlock_create_ruleset: %s\n", strerror(errno));
        return 2;
    }

    /* rw on workspace + scratch. */
    if (allow_path(rs, "/work", fs_all) < 0) return 2;
    if (allow_path(rs, "/tmp",  fs_all) < 0) return 2;

    /* ro on system trees the binary needs to load libs + read config. */
    const char *ro_paths[] = {
        "/usr", "/etc", "/lib", "/lib64", "/bin", "/sbin",
        "/proc/self", "/sys/devices/system/cpu",
        NULL
    };
    for (const char **p = ro_paths; *p; p++) {
        if (allow_path(rs, *p, fs_ro) < 0) return 2;
    }

    /* PR_SET_NO_NEW_PRIVS is MANDATORY before landlock_restrict_self.
     * Without it the kernel refuses with EPERM. */
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) {
        fprintf(stderr, "exec-init: PR_SET_NO_NEW_PRIVS: %s\n", strerror(errno));
        return 2;
    }

    if (ll_restrict(rs, 0) < 0) {
        fprintf(stderr, "exec-init: landlock_restrict_self: %s\n", strerror(errno));
        return 2;
    }
    close(rs);

    /* Resource limits -- belt and braces vs. the Quadlet PodmanArgs. */
    struct rlimit r;
    r.rlim_cur = r.rlim_max = 8ULL << 30; setrlimit(RLIMIT_AS,     &r);
    r.rlim_cur = r.rlim_max = 1024;       setrlimit(RLIMIT_NPROC,  &r);
    r.rlim_cur = r.rlim_max = 4096;       setrlimit(RLIMIT_NOFILE, &r);
    r.rlim_cur = r.rlim_max = 2ULL << 30; setrlimit(RLIMIT_FSIZE,  &r);

    /* Suggest the OOM killer pick us before the parent agent. */
    int oom_fd = open("/proc/self/oom_score_adj", O_WRONLY);
    if (oom_fd >= 0) {
        (void)!write(oom_fd, "500\n", 4);
        close(oom_fd);
    }

    execvp(argv[1], &argv[1]);
    fprintf(stderr, "exec-init: execvp(%s): %s\n", argv[1], strerror(errno));
    return 2;
}
