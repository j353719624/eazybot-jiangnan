/*
 * EazyBot-jiangnan 桌面启动器（macOS, x86_64）。
 *
 * 关键约束：LaunchServices 只把可执行文件位于 Contents/MacOS/ 下的进程
 * 归属到 .app 身份。python 解释器若从 Resources/env/bin/ 启动，Dock 会
 * 出现第二个独立图标。因此这里 exec 到 Contents/MacOS/EazyBot-jiangnan
 * （venv python 的真身副本），并用 __PYVENV_LAUNCHER__ 指回 venv 内的
 * python，使 CPython 的 pyvenv.cfg / site-packages 解析保持正确。
 *
 * 环境变量通过显式构建的 envp 传给 execve，不依赖 setenv 与全局
 * environ 的同步行为。
 */
#include <mach-o/dyld.h>
#include <crt_externs.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>

#define ENV_EXTRA_SLOTS 16

static void env_put(char **envp, int *n, const char *kv) {
    size_t klen = strcspn(kv, "=");
    for (int i = 0; i < *n; i++) {
        if (strncmp(envp[i], kv, klen) == 0 && envp[i][klen] == '=') {
            envp[i] = (char *)kv;
            return;
        }
    }
    envp[(*n)++] = (char *)kv;
}

static char *_kv(const char *key, const char *value) {
    size_t len = strlen(key) + 1 + strlen(value) + 1;
    char *out = malloc(len);
    if (!out) {
        return NULL;
    }
    snprintf(out, len, "%s=%s", key, value);
    return out;
}

int main(int argc, char **argv) {
    char self[PATH_MAX];
    uint32_t size = sizeof(self);
    if (_NSGetExecutablePath(self, &size) != 0) {
        return 1;
    }
    char self_real[PATH_MAX];
    if (!realpath(self, self_real)) {
        return 1;
    }

    char contents[PATH_MAX];
    snprintf(contents, sizeof(contents), "%s", self_real);
    char *slash = strrchr(contents, '/');
    if (!slash) {
        return 1;
    }
    *slash = '\0'; /* .../Contents/MacOS */
    slash = strrchr(contents, '/');
    if (!slash) {
        return 1;
    }
    *slash = '\0'; /* .../Contents */

    char resources[PATH_MAX];
    snprintf(resources, sizeof(resources), "%s/Resources", contents);

    char bootstrap[PATH_MAX];
    snprintf(bootstrap, sizeof(bootstrap), "%s/release_bootstrap.py", resources);

    char python_copy[PATH_MAX];
    snprintf(python_copy, sizeof(python_copy), "%s/MacOS/EazyBot-jiangnan", contents);

    char venv_python[PATH_MAX];
    snprintf(venv_python, sizeof(venv_python), "%s/env/bin/EazyBot-jiangnan", resources);

    /* 构建显式 envp：继承现有环境，再覆盖/追加本启动器的键 */
    char **oldenv = *_NSGetEnviron();
    int oldn = 0;
    while (oldenv[oldn]) {
        oldn++;
    }
    char **envp = malloc((oldn + ENV_EXTRA_SLOTS + 1) * sizeof(char *));
    if (!envp) {
        return 1;
    }
    int en = 0;
    for (int i = 0; i < oldn; i++) {
        envp[en++] = oldenv[i];
    }

    char buf[PATH_MAX];
    char *kv;
    int failed = 0;

    snprintf(buf, sizeof(buf), "%s/env/bin/EazyBot-jiangnan", resources);
    if ((kv = _kv("__PYVENV_LAUNCHER__", buf))) { env_put(envp, &en, kv); } else { failed = 1; }
    if ((kv = _kv("EAZYBOT_MACOS_PYTHON", python_copy))) { env_put(envp, &en, kv); } else { failed = 1; }
    if ((kv = _kv("PYTHONNOUSERSITE", "1"))) { env_put(envp, &en, kv); } else { failed = 1; }
    if ((kv = _kv("EAZYBOT_DESKTOP_APP", "1"))) { env_put(envp, &en, kv); } else { failed = 1; }
    snprintf(buf, sizeof(buf), "%s/release.env", resources);
    if ((kv = _kv("EAZYBOT_RELEASE_ENV_FILE", buf))) { env_put(envp, &en, kv); } else { failed = 1; }
    if ((kv = _kv("NPM_CONFIG_REGISTRY", "https://registry.npmmirror.com"))) { env_put(envp, &en, kv); } else { failed = 1; }
    if ((kv = _kv("PIP_INDEX_URL", "https://mirrors.aliyun.com/pypi/simple/"))) { env_put(envp, &en, kv); } else { failed = 1; }
    if (failed) {
        return 1;
    }
    envp[en] = NULL;

    char *child_argv[5];
    int n = 0;
    child_argv[n++] = (char *)"EazyBot-jiangnan";
    child_argv[n++] = bootstrap;
    child_argv[n++] = (char *)"desktop";
    for (int i = 1; i < argc && n < 4; i++) {
        child_argv[n++] = argv[i];
    }
    child_argv[n] = NULL;

    execve(python_copy, child_argv, envp);
    /* 兜底：MacOS 副本缺失时退回 venv python（旧行为） */
    execve(venv_python, child_argv, envp);
    return 1;
}
