# Build on Windows with: python -m PyInstaller packaging/AulaOS.spec --noconfirm --clean
from pathlib import Path
root = Path(SPECPATH).parent
lab = root / 'lab'
a = Analysis([str(lab / 'launcher.py')], pathex=[str(lab)],
             binaries=[], datas=[(str(lab / 'assets' / 'class_slide.pptx.b64'), 'assets')],
             hiddenimports=['sounddevice'], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=['pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AulaOS',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='AulaOS')
