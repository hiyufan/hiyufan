"""Build an offline, single-file HTML and an editable source bundle. Standard library only."""
from base64 import b64encode
import mimetypes
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'dist'
OUTPUT.mkdir(parents=True, exist_ok=True)


def data_url(relative: str) -> str:
    path = ROOT / relative
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,{b64encode(path.read_bytes()).decode()}'


html = (ROOT / 'index.html').read_text()
css = (ROOT / 'styles.css').read_text()
script = (ROOT / 'app.js').read_text()
css = re.sub(r"url\((['\"]?)(assets/[^)'\"]+)\1\)", lambda m: f'url("{data_url(m[2])}")', css)
html = re.sub(r'(src|href)="(assets/[^"]+)"', lambda m: f'{m[1]}="{data_url(m[2])}"', html)
html = html.replace('<link rel="stylesheet" href="styles.css">', f'<style>\n{css}\n</style>')
html = html.replace('<script src="app.js"></script>', '<script>\n' + script.replace('</script', '<\\/script') + '\n</script>')
licenses = '\n\n'.join(p.name + '\n' + p.read_text() for p in sorted((ROOT / 'assets').glob('OFL*.txt')))
html = html.replace('</body>', f'<script type="text/plain" id="bundled-font-licenses">{licenses}</script>\n</body>')
single = OUTPUT / '捷修云项目演示.html'
single.write_text(html)
archive = OUTPUT / '捷修云项目演示-源码与素材.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(single, f'捷修云项目演示/{single.name}')
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and OUTPUT not in path.parents:
            z.write(path, '捷修云项目演示/可编辑源码/' + path.relative_to(ROOT).as_posix())
print(single, single.stat().st_size)
print(archive, archive.stat().st_size)
