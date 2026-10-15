param([string]$Python = 'python', [string]$ISCC = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = (Join-Path $repo 'lab') + [IO.Path]::PathSeparator + $previousPythonPath
Push-Location $repo
try {
    if ($env:OS -ne 'Windows_NT') { throw 'Build on Windows, not by cross-compiling.' }
    & $Python -c "import struct; assert struct.calcsize('P') == 8, '64-bit Python required'"
    if ($LASTEXITCODE -ne 0) { throw 'Invalid Python architecture' }
    & $Python -m unittest discover -s lab/tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
    & $Python -m PyInstaller packaging/AulaOS.spec --noconfirm --clean
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    $report = Join-Path $repo 'dist\packaged-check.json'
    if (Test-Path $report) { Remove-Item $report }
    $exe = Join-Path $repo 'dist\AulaOS\AulaOS.exe'
    $proc = Start-Process -FilePath $exe -ArgumentList "--self-test `"$report`" --check-gui" -PassThru
    if (-not $proc.WaitForExit(120000)) { $proc.Kill(); throw 'Packaged check timed out' }
    if ($proc.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Packaged check failed' }
    $result = Get-Content $report -Raw | ConvertFrom-Json
    if (-not $result.ok) { throw 'Packaged check report failed' }
    if (-not (Test-Path $ISCC)) { throw 'Inno Setup 6 compiler not found' }
    $version = & $Python -c "from version import VERSION; print(VERSION)"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read application version' }
    & $ISCC "/DAppVersion=$version" packaging/AulaOS.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
    & $Python -m pip freeze | Set-Content dist/build-dependencies.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency inventory failed' }
    Get-FileHash dist/installer/*.exe -Algorithm SHA256 | Format-List | Out-File dist/SHA256.txt
} finally { Pop-Location; $env:PYTHONPATH = $previousPythonPath }
