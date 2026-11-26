$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$App = Join-Path $env:LOCALAPPDATA 'iwantMP7'
$Bin = Join-Path $App 'bin'
$PyFile = Join-Path $App 'iwantMP7.py'
$Base = 'https://raw.githubusercontent.com/SyntaxNon/IWantMP7/main/'

New-Item -ItemType Directory -Force -Path $Bin | Out-Null

function Fetch([string]$Url, [string]$Out) {
    if (Test-Path $Out) { return }
    Write-Host "fetching: $Out" -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing -TimeoutSec 180
}

Fetch ($Base + 'iwantMP7.py') $PyFile
Fetch 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' (Join-Path $Bin 'yt-dlp.exe')
Fetch 'https://raw.githubusercontent.com/Overv/WebCraft/master/style/minecraftia.ttf' (Join-Path $Bin 'minecraftia.ttf')

if (-not (Test-Path (Join-Path $Bin 'ffmpeg.exe'))) {
    $zip = Join-Path $env:TEMP 'iwant-ffmpeg.zip'
    $tmp = Join-Path $env:TEMP 'iwant-ffmpeg-extract'
    $mirrors = @(
        'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
        'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'
    )
    $ok = $false
    foreach ($url in $mirrors) {
        for ($attempt = 1; $attempt -le 2 -and -not $ok; $attempt++) {
            Remove-Item $zip -Force -ErrorAction SilentlyContinue
            if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
            try {
                Write-Host "fetching ffmpeg: $url" -ForegroundColor DarkGray
                Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing -TimeoutSec 300
                $stream = [IO.File]::OpenRead($zip)
                $buf = New-Object byte[] 4
                $null = $stream.Read($buf, 0, 4)
                $stream.Dispose()
                if ($buf[0] -ne 0x50 -or $buf[1] -ne 0x4B) { throw 'not a zip archive' }
                if ((Get-Item $zip).Length -lt 10MB) { throw 'archive too small' }
                New-Item -ItemType Directory -Force -Path $tmp | Out-Null
                if (Get-Command tar.exe -ErrorAction SilentlyContinue) {
                    & tar.exe -xf $zip -C $tmp
                    if ($LASTEXITCODE -ne 0) { throw 'tar extract failed' }
                } else {
                    Add-Type -AssemblyName System.IO.Compression.FileSystem
                    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $tmp)
                }
                $exe = Get-ChildItem $tmp -Recurse -Filter ffmpeg.exe | Select-Object -First 1
                if (-not $exe) { throw 'ffmpeg.exe not found in archive' }
                Copy-Item $exe.FullName (Join-Path $Bin 'ffmpeg.exe') -Force
                $ok = $true
            } catch {
                Write-Host "ffmpeg attempt $attempt failed: $($_.Exception.Message)" -ForegroundColor DarkGray
            }
        }
        if ($ok) { break }
    }
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    if (-not $ok) { throw 'could not install ffmpeg.exe' }
}

$fontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
New-Item -ItemType Directory -Force -Path $fontDir | Out-Null
Copy-Item (Join-Path $Bin 'minecraftia.ttf') (Join-Path $fontDir 'Minecraftia-Regular.ttf') -Force
New-ItemProperty -Force -Path 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts' -Name 'Minecraftia (TrueType)' -Value 'Minecraftia-Regular.ttf' | Out-Null
New-ItemProperty -Force -Path 'HKCU:\Console' -Name 'FaceName' -Value 'Minecraftia' | Out-Null
New-ItemProperty -Force -Path 'HKCU:\Console' -Name 'FontFamily' -PropertyType DWord -Value 0 | Out-Null
New-ItemProperty -Force -Path 'HKCU:\Console' -Name 'FontSize' -PropertyType DWord -Value 0x00100010 | Out-Null
New-ItemProperty -Force -Path 'HKCU:\Console' -Name 'ScreenColors' -PropertyType DWord -Value 0x000E | Out-Null

$PythonDir = Join-Path $App 'python'
$PythonExe = Join-Path $PythonDir 'python.exe'
if (-not (Test-Path $PythonExe)) {
    $pyZip = Join-Path $env:TEMP 'iwant-python.zip'
    $pyUrl = 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip'
    Write-Host 'installing python...' -ForegroundColor Cyan
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyZip -UseBasicParsing -TimeoutSec 300
    $stream = [IO.File]::OpenRead($pyZip)
    $buf = New-Object byte[] 4
    $null = $stream.Read($buf, 0, 4)
    $stream.Dispose()
    if ($buf[0] -ne 0x50 -or $buf[1] -ne 0x4B) { throw 'python archive is not a zip file' }
    if ((Get-Item $pyZip).Length -lt 5MB) { throw 'python archive too small' }
    New-Item -ItemType Directory -Force -Path $PythonDir | Out-Null
    if (Get-Command tar.exe -ErrorAction SilentlyContinue) {
        & tar.exe -xf $pyZip -C $PythonDir
        if ($LASTEXITCODE -ne 0) { throw 'python extract failed' }
    } else {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($pyZip, $PythonDir)
    }
    Remove-Item $pyZip -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $PythonExe)) { throw 'python.exe not found in archive' }
}

$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
if (-not (Test-Path $profilePath)) { New-Item -ItemType File -Force -Path $profilePath | Out-Null }
$lines = @(Get-Content -LiteralPath $profilePath -ErrorAction SilentlyContinue)
$lines = @($lines | Where-Object { $_ -notmatch 'function iwant' -and $_ -notmatch '# IWantMP7' -and $_ -notmatch '# iwantMP7' })
$fn = "function iwant { & `"$PythonExe`" -X utf8 `"$PyFile`" }"
$content = ($lines -join "`n")
if ($content) { $content += "`n" }
$content += "# IWantMP7`n$fn`n"
[IO.File]::WriteAllText($profilePath, $content, [Text.UTF8Encoding]::new($false))

Get-ChildItem -LiteralPath $App -Recurse -File | Unblock-File -ErrorAction SilentlyContinue
try { Add-MpPreference -ExclusionPath $App -ErrorAction Stop | Out-Null } catch { }

Write-Host 'IWantMP7 ready. type iwant from any PowerShell folder.' -ForegroundColor Green
& $PythonExe -X utf8 $PyFile
