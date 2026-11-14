#!/usr/bin/env python3
import hashlib, io, json, pathlib, subprocess, sys, tarfile, urllib.request

base = sys.argv[1]
changed = subprocess.check_output(["git", "diff", "--name-only", f"{base}...HEAD"], text=True).splitlines()
sources = [pathlib.Path(name) for name in changed if name.startswith("modules/") and name.endswith("/source.json")]
if not sources:
    print("PASS: no source.json changed; unrelated registry update")
    raise SystemExit(0)
for path in sources:
    source = json.loads(path.read_text())
    url = source.get("docs_url", "")
    if not url.startswith("https://"):
        raise SystemExit(f"unsupported docs_url: {path}")
    request = urllib.request.Request(url, headers={"User-Agent": "bcr-published-docs-review"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
        members = [item for item in archive.getmembers() if item.isfile() and item.name.endswith(".binaryproto")]
        if not members:
            raise SystemExit(f"documentation archive has no binaryproto: {path}")
        for member in members:
            if pathlib.PurePosixPath(member.name).is_absolute() or ".." in pathlib.PurePosixPath(member.name).parts:
                raise SystemExit(f"unsafe archive member: {member.name}")
            if not archive.extractfile(member).read():
                raise SystemExit(f"empty binaryproto: {member.name}")
    print(f"PASS reviewed docs {path}: sha256={hashlib.sha256(payload).hexdigest()} files={len(members)}")
