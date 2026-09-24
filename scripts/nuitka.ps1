Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Set-Location $projectRoot

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
