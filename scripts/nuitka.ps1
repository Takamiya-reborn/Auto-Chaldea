Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Set-Location $projectRoot

# 清理占用打包输出目录的残留进程（如上次打包产物拉起的 adb.exe），避免 Nuitka 覆盖文件时报 WinError 32
$buildDir = Join-Path $projectRoot "build"
if (Test-Path $buildDir) {
    $buildPrefix = (Get-Item $buildDir).FullName + "\"
    $strayProcesses = Get-CimInstance Win32_Process |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($buildPrefix, [System.StringComparison]::OrdinalIgnoreCase) }
    foreach ($process in $strayProcesses) {
        Write-Host "结束残留进程: $($process.ExecutablePath) (PID $($process.ProcessId))"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

$nuitkaArguments = @(
    "-m", "nuitka",
    "--standalone",
    "--windows-console-mode=disable",
    "--enable-plugins=pyside6",
    "--include-data-dir=assets=assets",
    "--include-data-files=assets/platform-tools/adb.exe=assets/platform-tools/adb.exe",
    "--include-data-files=assets/platform-tools/AdbWinApi.dll=assets/platform-tools/AdbWinApi.dll",
    "--include-data-files=assets/platform-tools/AdbWinUsbApi.dll=assets/platform-tools/AdbWinUsbApi.dll",
    "--python-flag=-O",
    "--lto=yes",
    "--output-dir=build",
    "--output-filename=Auto-Chaldea.exe",
    "main.py"
)

& uv run python @nuitkaArguments
if ($LASTEXITCODE -ne 0) {
    throw "Nuitka 打包失败，退出码: $LASTEXITCODE"
}
