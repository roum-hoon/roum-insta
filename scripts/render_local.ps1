# 심의용 초안 폴더의 post.json -> slide-01.jpg ... (1080x1350) 를 이 컴퓨터의 Edge로 렌더한다.
# 사용법: & .\scripts\render_local.ps1 -Draft "..\심의대기\2026-11-25_보험금찾기"
param([Parameter(Mandatory = $true)][string]$Draft)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$root = Split-Path $PSScriptRoot -Parent
$edge = @("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "C:\Program Files\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw "Edge를 찾을 수 없습니다." }

$draftDir = (Resolve-Path $Draft).Path
$post = Get-Content (Join-Path $draftDir "post.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$tmplName = if ($post.template) { $post.template } else { "customer" }
$tmpl = Get-Content (Join-Path $root "templates\$tmplName.html") -Raw -Encoding UTF8
$tmp = Join-Path $env:TEMP ("roum-render-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $tmp | Out-Null
Get-ChildItem $draftDir -Filter "slide-*.jpg" | Remove-Item -Force

$total = $post.slides.Count
$utf8 = New-Object System.Text.UTF8Encoding $false
$jpgCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
$encParams = New-Object System.Drawing.Imaging.EncoderParameters 1
$encParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality, [long]92)

for ($i = 0; $i -lt $total; $i++) {
  $n = $i + 1
  $data = [ordered]@{ slide = $post.slides[$i]; index = $n; total = $total; handle = $post.handle; review_no = "$($post.review_no)" }
  $json = $data | ConvertTo-Json -Depth 8 -Compress
  $html = $tmpl.Replace("/*__DATA__*/null", $json)
  $htmlPath = Join-Path $tmp "slide-$n.html"
  [IO.File]::WriteAllText($htmlPath, $html, $utf8)
  $png = Join-Path $tmp "slide-$n.png"
  $uri = ([Uri]$htmlPath).AbsoluteUri
  $edgeArgs = @("--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=1080,1350", "--virtual-time-budget=6000", "--user-data-dir=`"$tmp\profile`"", "--screenshot=`"$png`"", "`"$uri`"")
  Start-Process -FilePath $edge -ArgumentList $edgeArgs -Wait -WindowStyle Hidden -RedirectStandardError (Join-Path $tmp "edge.log")
  for ($t = 0; $t -lt 30 -and -not (Test-Path $png); $t++) { Start-Sleep -Milliseconds 300 }
  if (-not (Test-Path $png)) { throw "$n 번째 장 렌더 실패" }
  $img = [System.Drawing.Image]::FromFile($png)
  $out = Join-Path $draftDir ("slide-{0:D2}.jpg" -f $n)
  $img.Save($out, $jpgCodec, $encParams)
  $img.Dispose()
}
Remove-Item $tmp -Recurse -Force
"$total 장 렌더 완료: $draftDir"
