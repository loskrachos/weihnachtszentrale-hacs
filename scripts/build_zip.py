"""Build a deterministic installation ZIP from one checked-out source revision."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile
from datetime import datetime

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "custom_components/weihnachtszentrale/manifest.json").read_text())
version = manifest["version"]
release = json.loads((root / 'release.json').read_text())
if release['version'] != version:
    raise SystemExit('release.json must match manifest version')
# A single 1980 timestamp across releases lets timestamp/size-based Python
# bytecode caches survive a same-size source change. Use the fixed release
# date instead: reproducible within a release, distinct between releases.
released_at = datetime.fromisoformat(release['released_at'])
archive_time = released_at.timetuple()[:6]
if released_at.year < 2026 or released_at.second % 2:
    raise SystemExit('Release time must be current and use an even ZIP second')
card = root / "custom_components/weihnachtszentrale/frontend" / ("weihnachtszentrale-card-v" + version.replace(".", "") + ".js")
if not card.is_file():
    raise SystemExit("Versioned frontend missing: " + card.name)
files = [p for p in (root / "custom_components").rglob("*")
         if p.is_file() and "__pycache__" not in p.parts and p.suffix != '.pyc'
         and p.name != '.DS_Store' and not p.name.startswith('._')]
files += [root / "README.md"]
files += [p for p in (root / "docs").glob("*.md")]
if (root / "dashboard.yaml").exists():
    files.append(root / "dashboard.yaml")
for p in files:
    if p.suffix == ".py":
        ast.parse(p.read_text(), filename=str(p))
out = root / "artifacts"
out.mkdir(exist_ok=True)
archive = out / ("weihnachtszentrale_v" + version + ".zip")
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        info = zipfile.ZipInfo(str(p.relative_to(root)), date_time=archive_time)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, p.read_bytes())
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:
        raise SystemExit("Invalid archive")
    for p in files:
        assert z.read(str(p.relative_to(root))) == p.read_bytes()
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(archive.with_suffix(".zip.sha256")).write_text(digest + "  " + archive.name + "\n")
print(archive.name + "  SHA256 " + digest)
