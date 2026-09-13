import zipfile, os, sys

ZIP = os.path.expanduser("media/金融分析助手-finance.zip")
DEST = "/tmp/finance_agent"

zf = zipfile.ZipFile(ZIP)
names = zf.namelist()
print("entries:", len(names))
for n in names[:5]:
    print(repr(n))

os.makedirs(DEST, exist_ok=True)
ok, fail = 0, 0
for info in zf.infolist():
    # Windows 打包时用反斜杠作为路径分隔符，且文件名是 GBK 编码
    raw = info.filename
    if not (info.flag_bits & 0x800):  # 没有 UTF-8 标志位 → 按 GBK 解码
        try:
            raw = raw.encode("cp437").decode("gbk")
        except Exception:
            pass
    clean = raw.replace("\\", "/").lstrip("/")
    # 防路径穿越
    target = os.path.normpath(os.path.join(DEST, clean))
    if not target.startswith(os.path.abspath(DEST)):
        print("skip unsafe:", raw)
        continue
    if raw.endswith("/") or raw.endswith("\\") or clean.endswith("/"):
        os.makedirs(target, exist_ok=True)
        continue
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        with open(target, "wb") as f:
            f.write(zf.read(info))
        ok += 1
    except Exception as e:
        fail += 1
        print("FAIL:", raw, e)

print(f"extracted ok={ok} fail={fail}")
for root, dirs, files in os.walk(DEST):
    level = root.replace(DEST, "").count(os.sep)
    if level <= 2:
        print("  " * level + os.path.basename(root) + "/")
        if level < 2:
            for fn in files[:10]:
                print("  " * (level + 1) + fn)
