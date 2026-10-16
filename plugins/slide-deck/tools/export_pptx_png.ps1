# 元 PPTX の各スライドを PowerPoint で 1280x720 PNG に書き出す（Windows + PowerPoint 必須）。
# compare_ref.py の参照画像として使う。
# Usage: pwsh tools/export_pptx_png.ps1 -Src <pptx> -OutDir <dir> [-From 1] [-To 0(=最後まで)]
param(
    [Parameter(Mandatory = $true)][string]$Src,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$From = 1,
    [int]$To = 0
)
$Src = (Resolve-Path $Src).Path
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Open($Src, $true, $false, $false)
try {
    if ($To -le 0) { $To = $pres.Slides.Count }
    for ($i = $From; $i -le $To; $i++) {
        $pres.Slides.Item($i).Export((Join-Path $OutDir ("slide_{0:D3}.png" -f $i)), "PNG", 1280, 720)
    }
} finally {
    $pres.Close(); $ppt.Quit()
}
Write-Output "exported $From-$To -> $OutDir"
