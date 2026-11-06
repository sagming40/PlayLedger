# measure-list.ps1 ─ 게임 200개 기준 목록 · 통계 응답 시간을 잰다 (REQUIREMENTS 6장 "1초 이내", PLAN M5)
# 임시 계정을 만들고 → API로 200개를 넣고 → 조합마다 재고 → 계정을 지운다. 실제 계정에는 손대지 않는다
# 비유: 빈 창고를 하나 빌려 상자 200개를 쌓아 보고, 물건 꺼내는 데 몇 초 걸리는지 잰 뒤 창고를 반납한다
#
# 쓰는 법 (저장소 맨 위에서):
#   powershell -File scripts/measure-list.ps1                                  운영 (https://play.sagming.com)
#   powershell -File scripts/measure-list.ps1 -BaseUrl http://localhost:8001   로컬 개발 서버
#
# - 이메일 · 비밀번호는 실행 중에 묻는다(비밀번호는 가려진 입력). 화면 · 파일에 남기지 않는다
# - 이미 있는 이메일이면 멈춘다 ─ 실제 계정을 측정 데이터로 더럽히거나 지우지 않게
# - 기록 등록은 1분에 60개 제한이 있어서(core/rate_limit.py) 200개에 약 4분 걸린다. 실제 사용자와 같은 길로 넣으려고 일부러 기다린다
# - 지운 뒤에도 매일 백업에는 최대 14일 남는다(개인정보 안내). 넣는 값은 모두 지어낸 것이다
# - 시험(터미널 없이 돌릴 때)용: -Email, 환경 변수 MEASURE_PASSWORD, -DeleteAfter(방금 만든 임시 계정을 묻지 않고 지움)
#
# 이 파일은 UTF-8 BOM이 있어야 한다. Windows PowerShell 5.1은 BOM이 없으면 한글을 CP949로 읽어 깨진다

param(
	[string]$BaseUrl = 'https://play.sagming.com',
	[int]$Count = 200,
	[int]$Repeat = 20,
	[string]$Email = '',
	[switch]$DeleteAfter
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Inv = [Globalization.CultureInfo]::InvariantCulture
$BaseUrl = $BaseUrl.TrimEnd('/')

function Say([string]$msg) { Write-Host "[measure] $msg" }

# PowerShell 5.1의 Invoke-RestMethod는 문자열 본문을 한글이 깨지게 보낸다 ─ UTF-8 바이트로 넘긴다
function Api([string]$Method, [string]$Path, $Body = $null, [string]$Token = $null) {
	$req = @{ Method = $Method; Uri = "$BaseUrl$Path"; ContentType = 'application/json; charset=utf-8' }
	if ($Token) { $req.Headers = @{ Authorization = "Bearer $Token" } }
	if ($null -ne $Body) { $req.Body = [Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Compress -Depth 5)) }
	Invoke-RestMethod @req
}

function StatusOf($err) {
	if ($err.Exception.Response) { return [int]$err.Exception.Response.StatusCode }
	return 0
}

function Login([string]$Email, [string]$Password) {
	(Api POST '/api/auth/login' @{ email = $Email; password = $Password }).access_token
}

# ── 0. 서버가 살아 있는지 ──
$health = Api GET '/api/health'
Say "대상: $BaseUrl (health: $($health.status))"

# ── 1. 임시 계정 ──
Say '측정용 임시 계정을 새로 만든다. 지어낸 이메일을 쓴다 (예: perf-20261106@example.com)'
if (-not $Email) { $Email = (Read-Host '이메일').Trim() }
if ($env:MEASURE_PASSWORD) { $Password = $env:MEASURE_PASSWORD }
else {
	$secure = Read-Host '비밀번호 (8자 이상, 가려짐)' -AsSecureString
	$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
	try { $Password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
	finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

try {
	Api POST '/api/auth/register' @{ email = $Email; password = $Password; nickname = '측정용' } | Out-Null
}
catch {
	$code = StatusOf $_
	if ($code -eq 409) { throw '이미 있는 이메일이다 ─ 실제 계정일 수 있어서 멈춘다. 새 이메일로 다시 실행한다' }
	throw "가입 실패 (상태 $code): $($_.ErrorDetails.Message)"
}
$Created = $true
Say "가입함: $Email"

$started = Get-Date
try {
	$Token = Login $Email $Password
	$before = Api GET '/api/entries?limit=1' $null $Token
	if ($before.total -ne 0) { throw "새 계정인데 기록이 $($before.total)개 있다 ─ 멈춘다" }

	# ── 2. 200개 넣기 ── 상태 5가지 · 장르 섞기 · 구매일 · 가격 · 플레이타임을 고르게 (같은 씨앗 = 매번 같은 데이터)
	$genres = @(Api GET '/api/genres' $null $Token | ForEach-Object { $_.id })   # 장르 목록도 로그인 필요
	Say "장르 $($genres.Count)개를 섞어 $Count 개를 넣는다 (약 $([math]::Ceiling($Count * 1.05 / 60))분)"
	$rand = New-Object System.Random 20261106
	$statuses = 'BACKLOG', 'PLAYING', 'CLEARED', 'ON_HOLD', 'DROPPED'
	$today = (Get-Date).Date
	for ($i = 1; $i -le $Count; $i++) {
		$body = @{
			title            = ('측정용 게임 {0:D3}' -f $i)
			status           = $statuses[$i % 5]
			playtime_minutes = $rand.Next(0, 200 * 60)
		}
		if ($rand.Next(10) -gt 0) { $body.purchased_at = $today.AddDays(-$rand.Next(1, 7 * 365)).ToString('yyyy-MM-dd') }
		if ($rand.Next(10) -gt 0) { $body.purchase_price = $rand.Next(0, 80) * 1000 }
		if ($rand.Next(3) -eq 0) { $body.rating = $rand.Next(1, 6) }
		if ($genres.Count -gt 0) {
			$pick = @($genres[$rand.Next($genres.Count)])
			if ($genres.Count -gt 1 -and $rand.Next(2) -eq 0) { $pick += $genres[$rand.Next($genres.Count)] }
			$body.genre_ids = @($pick | Select-Object -Unique)
		}
		while ($true) {
			try { Api POST '/api/entries' $body $Token | Out-Null; break }
			catch {
				$code = StatusOf $_
				if ($code -eq 429) { Start-Sleep -Seconds 5; continue }
				if ($code -eq 401) { $Token = Login $Email $Password; continue }   # access 토큰 15분
				throw "등록 실패 ${i}번째 (상태 $code): $($_.ErrorDetails.Message)"
			}
		}
		if ($i % 20 -eq 0) { Say "  $i / $Count" }
		Start-Sleep -Milliseconds 1000
	}
	$after = Api GET '/api/entries?limit=1' $null $Token
	if ($after.total -ne $Count) { throw "넣은 뒤 개수가 $($after.total)개다 ($Count 개여야 한다)" }
	Say "넣음: $($after.total)개 ($([int]((Get-Date) - $started).TotalSeconds)초)"

	# ── 3. 재기 ── curl의 단계별 시각으로 "연결 · TLS"와 "서버 처리"를 나눈다
	# server = 첫 바이트 - 요청 보낼 준비 끝(time_pretransfer) ≈ 서버가 처리한 시간 + 왕복 한 번
	# total  = 새 연결부터 끝까지 (브라우저는 연결을 재사용하니 실제 화면보다 길게 나온다 ─ 보수적인 값)
	$Token = Login $Email $Password
	$g = if ($genres.Count -gt 0) { $genres[0] } else { $null }
	$cases = [ordered]@{
		'목록 기본(최근 수정순)'  = '/api/entries?limit=20&offset=0'
		'정렬 구매일'             = '/api/entries?limit=20&offset=0&sort=purchased'
		'정렬 제목'               = '/api/entries?limit=20&offset=0&sort=title'
		'정렬 플레이타임'         = '/api/entries?limit=20&offset=0&sort=playtime'
		'상태 미시작'             = '/api/entries?limit=20&offset=0&status=BACKLOG'
		'마지막 쪽(offset 180)'   = '/api/entries?limit=20&offset=180'
		'상태별 개수(limit=1)'    = '/api/entries?limit=1&offset=0&status=PLAYING'
		'통계'                    = "/api/stats?today=$($today.ToString('yyyy-MM-dd'))"
	}
	if ($g) {
		$cases['장르 필터'] = "/api/entries?limit=20&offset=0&genre=$g"
		$cases['상태 + 장르'] = "/api/entries?limit=20&offset=0&status=BACKLOG&genre=$g"
	}

	$fmt = '%{http_code} %{time_pretransfer} %{time_starttransfer} %{time_total}'
	$rows = foreach ($name in $cases.Keys) {
		$url = "$BaseUrl$($cases[$name])"
		$server = @(); $total = @()
		for ($k = 0; $k -le $Repeat; $k++) {
			$out = & curl.exe -s -o NUL -w $fmt -H "Authorization: Bearer $Token" $url
			$p = $out.Trim() -split ' '
			if ($p[0] -ne '200') { throw "$name 응답 $($p[0]) ($url)" }
			if ($k -eq 0) { continue }   # 첫 번은 버린다 (DB 캐시 데우기)
			$server += ([double]::Parse($p[2], $Inv) - [double]::Parse($p[1], $Inv)) * 1000
			$total += [double]::Parse($p[3], $Inv) * 1000
		}
		$s = $server | Sort-Object; $t = $total | Sort-Object
		[pscustomobject]@{
			'조합'          = $name
			'서버 중간(ms)' = [math]::Round($s[[int]($s.Count / 2)])
			'서버 최대(ms)' = [math]::Round($s[-1])
			'전체 중간(ms)' = [math]::Round($t[[int]($t.Count / 2)])
			'전체 최대(ms)' = [math]::Round($t[-1])
		}
	}
	Write-Host ''
	Say "결과 ─ 기록 $Count 개, 조합마다 $Repeat 번 (첫 번 제외)"
	$rows | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
	$worst = ($rows | Measure-Object -Property '전체 최대(ms)' -Maximum).Maximum
	if ($worst -lt 1000) { Say "판정: 통과 ─ 가장 느린 것 $worst ms < 1000 ms" }
	else { Say "판정: 실패 ─ 가장 느린 것 $worst ms" }
}
finally {
	# ── 4. 정리 ── 중간에 실패해도 임시 계정을 지울지 묻는다
	if ($Created) {
		Write-Host ''
		if ($DeleteAfter) { $answer = 'delete' }
		else { $answer = Read-Host "임시 계정 $Email 과 기록을 지울까? 지우려면 delete 입력" }
		if ($answer -eq 'delete') {
			$t = Login $Email $Password
			Api DELETE '/api/auth/me' @{ password = $Password } $t | Out-Null
			try { Login $Email $Password | Out-Null; Say '경고: 지운 계정으로 아직 로그인된다' }
			catch { Say "지움: 지운 계정으로 로그인하면 $(StatusOf $_) (401이어야 한다)" }
		}
		else { Say "남겨 둠: 나중에 화면 설정 → 계정 삭제로 지운다 ($Email)" }
	}
	$Password = $null
}
