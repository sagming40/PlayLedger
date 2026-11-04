# deploy.ps1 ─ PC 쪽 배포: 확인 → CI 통과 기다리기 → play-release 한 번 → 밖에서 확인 (SERVER 2절)
# task deploy로 부른다. 서버 쪽 일(받기 · 백업 · 마이그레이션 · 교체 · 되돌리기)은 deploy/play-release가 한다
# 비유: 출고 전 검수 ─ 창고에 있는 물건이 맞는지(깨끗한 main), 검사에 합격했는지(CI) 본 뒤에야 트럭을 부른다
#
# 쓰는 법:
#   task deploy                  배포
#   task deploy -- -DryRun       확인까지만 하고 서버에는 안 간다
#   task deploy -- -SshHost 별명  ~/.ssh/config의 다른 별명으로 (기본 play, SERVER 3.1절)
#
# 이 파일은 UTF-8 BOM이 있어야 한다. Windows PowerShell 5.1은 BOM이 없으면 한글을 CP949로 읽어 깨진다

param(
	[string]$SshHost = 'play',
	[switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
# PowerShell 5.1은 기기 설정에 따라 옛 TLS로 나가 GitHub에 거절당할 수 있다
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
# 직접 실행해도 task로 부른 것과 같게 저장소 맨 위에서 돈다
Set-Location (Split-Path -Parent $PSScriptRoot)

$Repo = 'sagming40/PlayLedger'
$Site = 'https://play.sagming.com'
# CI는 보통 2분 안에 끝난다(2026-11-04 다섯 번 100 ~ 132초)
$CiWaitSeconds = 600
# push 직후에는 CI 실행이 한동안 API에 안 보인다(2026-11-05: 30초에 없고 60초에 보임). 이만큼 지나도 없으면 없는 것으로 본다
$CiAppearSeconds = 180
# 로그인 없는 GitHub API는 한 시간에 60번까지다. 30초 간격이면 10분을 다 기다려도 20번이다
$PollSeconds = 30

function Fail([string]$msg) {
	Write-Host "[deploy] 실패: $msg" -ForegroundColor Yellow
	exit 1
}
function Log([string]$msg) { Write-Host "[deploy] $msg" }

# 바깥 프로그램(git · ssh)은 실패해도 PowerShell이 멈추지 않는다 → 종료 코드를 직접 본다
function Check([string]$what) {
	if ($LASTEXITCODE -ne 0) { Fail "$what (종료 코드 $LASTEXITCODE)" }
}

# 미커밋이 없고 지금 커밋이 origin/main과 같으면 그 커밋 번호를 돌려준다
# 기기가 3대라 push 안 한 코드나 뒤처진 코드로 운영을 덮어쓰는 일을 막는다
function Get-CleanCommit {
	git fetch --quiet origin main; Check 'git fetch'
	$dirty = git status --porcelain; Check 'git status'
	if ($dirty) { Fail "커밋 안 한 변경이 있다 (새 파일 포함) ─ 커밋 · push 뒤 다시`n$($dirty -join "`n")" }
	$head = git rev-parse HEAD; Check 'git rev-parse HEAD'
	$origin = git rev-parse origin/main; Check 'git rev-parse origin/main'
	if ($head -ne $origin) {
		Fail "지금 커밋($($head.Substring(0, 7)))이 origin/main($($origin.Substring(0, 7)))과 다르다 ─ push 또는 pull 먼저"
	}
	return $head
}

# 그 커밋을 main에 push해서 돈 ci 실행 중 가장 최근 것. 저장소가 공개라 토큰이 필요 없다
function Get-CiRun([string]$sha) {
	$url = "https://api.github.com/repos/$Repo/actions/runs?branch=main&event=push&head_sha=$sha"
	try {
		$res = Invoke-RestMethod -Uri $url -TimeoutSec 20 -Headers @{ 'User-Agent' = 'PlayLedger-deploy'; 'Accept' = 'application/vnd.github+json' }
	} catch {
		# 합격 여부를 모르면 합격으로 치지 않는다
		Fail "CI 상태를 읽지 못했다 ($($_.Exception.Message)). 403이면 GitHub 요청 제한(시간당 60번)일 수 있다"
	}
	return $res.workflow_runs | Where-Object { $_.path -eq '.github/workflows/ci.yml' } | Sort-Object created_at -Descending | Select-Object -First 1
}

# 성공이면 돌아오고, 실패 · 시간 초과면 멈춘다. images는 test · web을 통과해야 도니까 ci 성공 = 이미지 있음
function Wait-Ci([string]$sha) {
	$started = Get-Date
	while ($true) {
		$run = Get-CiRun $sha
		$elapsed = [int]((Get-Date) - $started).TotalSeconds
		if (-not $run) {
			if ($elapsed -ge $CiAppearSeconds) { Fail "이 커밋의 ci 실행이 없다 ─ https://github.com/$Repo/actions" }
			Log "ci 실행이 아직 안 보인다 (${elapsed}초)"
		} elseif ($run.status -eq 'completed') {
			if ($run.conclusion -eq 'success') {
				Log "ci 성공 ─ $($run.html_url)"
				return
			}
			Fail "ci 결과가 $($run.conclusion) 이다 ─ $($run.html_url)"
		} else {
			if ($elapsed -ge $CiWaitSeconds) { Fail "ci가 ${CiWaitSeconds}초 안에 안 끝났다 ─ $($run.html_url)" }
			Log "ci $($run.status), 기다리는 중 (${elapsed}초, Ctrl+C로 그만둔다)"
		}
		Start-Sleep -Seconds $PollSeconds
	}
}

# ── 1. 확인 ──
$commit = Get-CleanCommit
Log "배포할 커밋: $commit"
Wait-Ci $commit

# 기다리는 동안 다른 기기가 push했으면 옛 커밋으로 운영을 덮어쓰게 된다 → 다시 본다
if ((Get-CleanCommit) -ne $commit) { Fail '기다리는 동안 커밋이 바뀌었다 ─ 다시 실행한다' }

$remote = "sudo play-release $commit"
if ($DryRun) {
	Log 'DryRun ─ 여기서 멈춘다. 실제로는:'
	Log "  ssh -t $SshHost `"$remote`""
	exit 0
}

# ── 2. 서버에서 실행 ── 되돌리기 · 동시 배포 잠금은 play-release가 맡는다
# -t: 터미널을 연결해야 서버의 sudo가 비밀번호를 물을 수 있다
Log '서버에서 play-release 실행 (passphrase · sudo 비밀번호를 물으면 입력)'
ssh -t $SshHost $remote; Check '서버 쪽 배포 ─ 위 [release] 줄을 본다'

# ── 3. 밖에서 확인 ── 서버 안에서 본 것과 별개로 사용자가 들어오는 길로 한 번 더 본다
try {
	$health = Invoke-RestMethod -Uri "$Site/api/health" -TimeoutSec 20
} catch {
	Fail "배포는 끝났는데 밖에서 $Site/api/health 를 못 읽었다 ($($_.Exception.Message))"
}
if ($health.status -ne 'ok') { Fail "배포는 끝났는데 헬스체크가 ok가 아니다 (status=$($health.status))" }
Log "끝: $commit ─ $Site (health ok)"
