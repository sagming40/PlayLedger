# 운영 서버

> **운영 서버를 어떻게 세팅했고 어떻게 배포 · 백업 · 복구하는지 적는 런북이다.** 실제로 친 명령과 나온 결과를 남긴다.
> 왜 이 구성인지는 [decisions/0012](decisions/0012-caddy-proxy.md) · [PLAN](PLAN.md) M5, 파일 원본은 `deploy/` · `server/Dockerfile` · `web/Dockerfile` · `web/deploy/Caddyfile`. 비밀값 · 서버 IP는 여기 적지 않는다.

## 1. 한눈에

| 항목 | 값 |
|---|---|
| 업체 · 위치 | Vultr · 서울. 12월에 AWS로 이사 예정 (전역 설정 "서버 이사 계획") |
| 서버 이름 | `play-1` (`cbt-1`과 분리) |
| 사양 | Shared CPU `vc2-1c-1gb` — 1 vCPU · 메모리 1GB · 월 $5 · Ubuntu 24.04 LTS · IPv4만 |
| 접속 | 일반 계정 `sagming40` + SSH 키만. root · 비밀번호 로그인 불가 |
| 도메인 | `play.sagming.com` (Cloudflare, DNS만 · 회색 구름) |
| 열린 문 | 22 · 80 · 443 |
| 앱 위치 | `/srv/playledger/` (`compose.yaml` · `.env` · `image.env`), 백업 `/var/backups/playledger/`(최근 14개) |
| 서버 밖 백업 | Cloudflare R2 버킷 `playledger-backups`, 14일 (3.9절, [decisions/0013](decisions/0013-r2-offsite-backup.md)) |
| 감시 | GitHub Actions `uptime` — 30분마다(7분 · 37분) 밖에서 `/api/health` 본문과 인증서 남은 날(20일 미만이면 실패)을 본다. 디스크 여유도 같은 본문의 `"disk"`로 본다(남은 공간 10% 미만이면 `low` → 실패). 실패하면 GitHub 메일. 저장소에 60일 커밋이 없으면 GitHub가 멈추니 Actions 화면에서 다시 켠다 |
| 정기 작업 | 백업 매일 04:30 KST(`play-backup.timer`), Steam 게임 목록 매주 일요일 05:30 KST(`play-steam-sync.timer`, 3.10절) |
| 기억할 날짜 | **2026-11-30 Vultr 크레딧 만료** — 그 전에 남길지 정한다. Stop은 요금이 계속 나간다, 없애려면 Destroy |

## 2. 평소에 쓰는 명령

**배포** — `main`에 push한 뒤 PC(저장소 폴더)에서. CI가 도는 중이면 끝날 때까지 기다린다:

```powershell
task deploy              # 미커밋 없음 → origin/main과 같음 → ci 성공 → play-release → 밖에서 /api/health
task deploy -- -DryRun   # 확인까지만
```

확인 하나라도 안 되면 이유를 말하고 멈춘다(`scripts/deploy.ps1`). Task가 없는 기기나 CI 결과와 상관없이 올려야 할 때는 직접 `ssh -t play "sudo play-release <전체 커밋>"`. 실패한 커밋은 이미지가 없어 서버가 받지 못하지만, `audit`만 실패한 커밋은 이미지가 있어서 `task deploy`만 멈춘다.

**상태 · 로그** (서버):

```bash
sudo play-compose ps
sudo play-compose logs api --tail 50
```

**게임 목록 미러링** (서버, 약 20초 ~ 몇 분). 매주 일요일에 타이머가 돌린다(3.10절). 손으로 돌릴 때는 배포 중이 아닐 때:

```bash
sudo play-compose run --rm api python -m app.scripts.sync_steam_apps
```

**백업 내려받기** (PC). 열쇠가 없으면 못 연다:

```powershell
New-Item -ItemType Directory -Force "$HOME\playledger-backups" | Out-Null
scp "play:/var/backups/playledger/*.dump.age" "$HOME\playledger-backups\"
```

**복구 리허설** (PC, Docker Desktop을 켠 뒤. 2026-11-06 처음 함, 5절). 운영은 읽기만 한다.

1. 서버에서 백업을 새로 만들고 바로 개수를 센다 ─ 그 사이에 기록이 바뀌지 않게 붙여서 친다:

```bash
sudo play-backup && sudo play-compose exec db psql -U playledger -d playledger -c "select (select count(*) from users) users, (select count(*) from games) games, (select count(*) from entries) entries, (select count(*) from genres) genres, (select count(*) from game_genres) game_genres, (select count(*) from refresh_tokens) refresh_tokens, (select version_num from alembic_version) alembic"
```

2. 위 "백업 내려받기" 뒤 PC에서 가장 최근 백업을 빈 임시 DB에 되살려 같은 개수를 센다. `steam_apps`는 구조만 백업하므로 0이 맞다(미러링으로 다시 채운다):

```powershell
$latest = Get-ChildItem "$HOME\playledger-backups\*.dump.age" | Sort-Object Name | Select-Object -Last 1
$dump = "$env:TEMP\play-restore.dump"
age -d -i "$HOME\playledger-backup.key" -o $dump $latest.FullName
docker run -d --rm --name play-restore -e POSTGRES_USER=playledger -e POSTGRES_PASSWORD=rehearsal -e POSTGRES_DB=playledger postgres:18
do { Start-Sleep 2; docker exec play-restore pg_isready -U playledger -d playledger -q } until ($LASTEXITCODE -eq 0)
Start-Sleep 3   # 첫 기동은 초기화 뒤 한 번 재시작한다 ─ 그 틈에 들어가지 않게
docker cp $dump play-restore:/tmp/r.dump
docker exec play-restore pg_restore -U playledger -d playledger --exit-on-error /tmp/r.dump; "pg_restore exit $LASTEXITCODE"
docker exec play-restore psql -U playledger -d playledger -c "select (select count(*) from users) users, (select count(*) from games) games, (select count(*) from entries) entries, (select count(*) from genres) genres, (select count(*) from game_genres) game_genres, (select count(*) from refresh_tokens) refresh_tokens, (select count(*) from steam_apps) steam_apps, (select version_num from alembic_version) alembic"
docker stop play-restore; Remove-Item $dump   # 풀린 덤프에는 이메일 · 비밀번호 해시가 있다. 반드시 지운다
```

**운영 복구** (`deploy/play-restore`). 운영 DB를 백업 시점으로 **바꾼다** ─ 그 뒤의 기록은 사라진다. 운영에서는 아직 돌려 보지 않았고, 내 PC의 운영 구성에서 시험했다(5절 2026-11-06).
열쇠는 PC에만 있어서, PC에서 풀어 서버의 내 홈으로 올린다. 04:30 백업과 일요일 05:30 ~ 05:45 게임 목록 타이머 시각은 피한다(게임 목록은 같은 잠금을 잡아서 "배포가 진행 중이다"로 멈춘다. 그러면 다시 친다).

```powershell
# PC ─ 되살릴 백업을 고른다. 가장 최근이 아니면 이름으로 고른다
$pick = Get-ChildItem "$HOME\playledger-backups\*.dump.age" | Sort-Object Name | Select-Object -Last 1
age -d -i "$HOME\playledger-backup.key" -o "$env:TEMP\restore.dump" $pick.FullName
scp "$env:TEMP\restore.dump" play:~/restore.dump; Remove-Item "$env:TEMP\restore.dump"
```

```bash
# 서버 ─ 덤프 확인 → restore 입력 → 지우기 전 백업 → api 멈춤 → DB 비우고 되살리기 → 마이그레이션 → api 시작 → 게임 목록
chmod 600 ~/restore.dump
sudo play-restore ~/restore.dump; rm -f ~/restore.dump    # 풀린 덤프다. 성공 · 실패와 상관없이 지운다
```

- 잠긴 `.dump.age`나 깨진 파일은 덤프 확인에서 멈추고 아무것도 안 바꾼다. `restore`가 아닌 답도 취소다
- 지우기 전에 지금 DB를 `play-backup`으로 한 번 더 뜬다. 잘못 되살렸으면 그 파일(`/var/backups/playledger/` 맨 끝)을 받아 같은 순서로 다시 한다
- 중간에 멈추면 api가 멈춘 채다(화면은 뜨고 `/api`는 502). 같은 명령을 다시 치면 된다 ─ DB가 없으면 지우기 전 백업을 건너뛰고 이어서 되살린다
- 백업이 지금 코드보다 옛 버전이면 마이그레이션이 따라 올린다. 백업은 `steam_apps`를 구조만 담아서 마지막에 게임 목록을 다시 받는다

**백업 상태** (서버). 실패해도 알려 주는 곳이 없다 ─ 가끔 본다:

```bash
systemctl list-timers 'play-*'               # 백업 · 게임 목록 타이머의 다음 · 지난 실행 시각
systemctl --failed                           # play-backup · play-steam-sync가 있으면 실패한 것 (R2만 실패해도 뜬다)
sudo journalctl -u play-backup -n 20         # 마지막 실행 출력 ([backup] R2에 올림: … 줄)
sudo journalctl -u play-steam-sync -n 5      # "받은 게임 …건 · steam_apps …행 · …초"
df -h /; sudo docker system df               # 디스크. 감시가 disk low로 실패했을 때 무엇이 큰지 본다
```

되돌리기: `play-release`는 새 버전이 살아나지 않으면 이전 커밋으로 스스로 돌아간다. 마이그레이션은 되돌리지 않는다(데이터를 잃을 수 있다). 표 때문에 옛 코드가 안 돌면 배포 직전 백업으로 복구한다.

## 3. 처음 세팅

> `cbt-journal`의 `docs/SERVER.md` 4장과 같은 순서이고, 줄마다 자세한 설명은 그쪽에 있다. 여기서는 다른 점과 왜 치는지만 적는다.
> 2026-11-04 회사 PC에서 전부 쳤다. 결과는 5절.

### 3.1 SSH 열쇠 (PC, 기기마다)

서버 전용 열쇠를 PC마다 따로 만든다. 잃어버린 PC의 열쇠만 뺄 수 있게.

```powershell
ssh-keygen -t ed25519 -f "$HOME\.ssh\play_vultr" -C "company-pc"   # passphrase를 넣는다
Get-Content "$HOME\.ssh\play_vultr.pub"                            # Vultr에 붙여 넣을 공개키
```

**다른 PC를 추가할 때** (서버는 이미 있다. 집 PC는 2026-11-04에 넣었다(5절), 노트북은 아직 안 함)

1. 그 PC에서 위 명령으로 열쇠를 만든다(`-C`는 `home-pc` · `laptop`).
2. 공개키 한 줄을 서버에 넣는다. 이미 접속되는 PC(회사 PC)로 `ssh play` 해서 치거나, Vultr 웹 콘솔(Server Information → View Console, root로 로그인)에서 친다. root · 비밀번호 SSH는 막혀 있어도 웹 콘솔은 된다.

   ```bash
   echo 'ssh-ed25519 AAAA…(한 줄 전체)' >> /home/sagming40/.ssh/authorized_keys
   ```

   `>>`(두 개)여야 한다. `>`(하나)면 다른 PC의 열쇠가 지워진다.
3. 그 PC의 `~/.ssh/config`에 `Host play`를 적는다. `User`는 `sagming40`, `IdentityFile`은 `~/.ssh/play_vultr`, `HostName`은 `play.sagming.com`으로 써도 된다.
4. `ssh play` → `sudo whoami`가 `root`면 끝. sudo 비밀번호는 PC가 달라도 같다.

### 3.2 서버 만들기 (Vultr 화면)

Deploy New Instance → Shared CPU · Seoul · Ubuntu 24.04 LTS x64 · `vc2-1c-1gb`(월 $5) · SSH Keys에 위 공개키 추가 · 이름 `play-1` · Auto Backups 끔(자체 백업이 있다) · IPv6 끔.

`~/.ssh/config`에 별명을 더한다(`<서버 IP>`는 실제 값, 저장소에 적지 않는다):

```text
Host play
    HostName <서버 IP>
    User root
    IdentityFile ~/.ssh/play_vultr
```

### 3.3 기본 세팅 (서버, root)

```bash
cloud-init status --wait
apt update && apt upgrade -y     # 설정 파일을 덮어쓸지 물으면 지금 것 유지(keep local), 재시작 질문은 Enter
reboot
```

```bash
ufw default deny incoming && ufw default allow outgoing
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp
ufw enable
adduser sagming40                # 묻는 비밀번호 = sudo 비밀번호
usermod -aG sudo sagming40
rsync --archive --chown=sagming40:sagming40 ~/.ssh /home/sagming40
```

`~/.ssh/config`의 `User`를 `sagming40`으로 바꾸고, **새 탭에서** `ssh play` → `sudo whoami`가 `root`인지 본 뒤 잠근다(기존 탭은 열어 둔다):

```bash
printf 'PermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n' | sudo tee /etc/ssh/sshd_config.d/00-hardening.conf
sudo sshd -t
sudo systemctl reload ssh
systemctl is-active unattended-upgrades    # active여야 보안 패치가 저절로 깔린다
```

### 3.4 Docker · 스왑 · age (서버)

```bash
sudo apt-get install -y ca-certificates curl age
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run --rm hello-world
```

`sagming40`을 `docker` 그룹에 넣지 않는다(root와 같다). 스왑은 Vultr가 만들어 두므로 확인만 하고 swappiness만 낮춘다:

```bash
swapon --show
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl --system | grep swappiness
```

### 3.5 DNS (Cloudflare 화면)

`sagming.com` → DNS → 레코드 추가: `A` · 이름 `play` · 서버 IP · **프록시 끔(회색 구름)**. 첫 배포 전에 한다 ─ Caddy가 켜지자마자 인증서를 받으러 간다.

```powershell
nslookup play.sagming.com 1.1.1.1    # 서버 IP가 나오면 된다
```

### 3.6 비밀값 · 운영 파일

PC에서 파일을 보낸다:

```powershell
# 저장소 폴더
scp deploy/prod.env.example deploy/play-compose deploy/play-release deploy/play-backup deploy/play-restore deploy/play-backup.service deploy/play-backup.timer play:~/
```

서버에서 설치하고 비밀값을 만든다. 비밀값은 화면 캡처 · 채팅에 내지 않는다:

```bash
sudo install -d -m 750 /srv/playledger
sudo install -m 600 ~/prod.env.example /srv/playledger/.env
sudo sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 32)/; s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" /srv/playledger/.env
sudo nano /srv/playledger/.env    # STEAM_API_KEY만 붙여 넣는다 (https://steamcommunity.com/dev/apikey)
sudo grep -c '=$' /srv/playledger/.env    # 빈 값 개수. 0이어야 한다 (값은 출력되지 않는다)
sudo install -m 755 ~/play-compose ~/play-release ~/play-backup ~/play-restore /usr/local/bin/
sudo install -m 644 ~/play-backup.service ~/play-backup.timer /etc/systemd/system/
rm ~/prod.env.example ~/play-compose ~/play-release ~/play-backup ~/play-restore ~/play-backup.service ~/play-backup.timer
```

### 3.7 백업 열쇠 (PC → 서버)

자물쇠(공개키)만 서버에 둔다. 서버가 털려도 백업은 못 연다. 개인키는 서버 · 저장소 · 대화 · 클라우드에 두지 않는다. 잃으면 그 전 백업은 못 연다.
**개인키는 지금 회사 PC `$HOME\playledger-backup.key`에만 있다.** 복구는 이 PC에서 하거나 USB로 옮긴다. 회사 PC를 못 쓰게 될 때를 대비한 사본을 아직 안 만들었다.

```powershell
age-keygen -o "$HOME\playledger-backup.key"
age-keygen -y "$HOME\playledger-backup.key"    # 서버에 넣을 age1… (비밀 아님)
```

```bash
sudo install -d -m 755 /etc/playledger
echo 'age1…' | sudo tee /etc/playledger/backup.pub
sudo chmod 644 /etc/playledger/backup.pub
sudo systemctl daemon-reload
sudo systemctl enable --now play-backup.timer
systemctl list-timers play-backup.timer
```

### 3.8 첫 배포

2절의 배포 명령 그대로. 끝나면:

```bash
sudo play-compose ps
sudo play-compose run --rm api python -m app.scripts.sync_steam_apps
sudo play-backup
```

### 3.9 서버 밖 백업 (Cloudflare R2)

왜 R2인지는 [decisions/0013](decisions/0013-r2-offsite-backup.md). 잠긴 파일을 그대로 올리므로 Cloudflare도 열 수 없다. 이 절을 하지 않으면 `play-backup`은 서버에만 둔다.

1. **Cloudflare 화면** (개인 Gmail 계정)
   - R2 → 시작하기. 무료 한도(10GB)라도 결제수단 등록을 요구할 수 있다
   - 버킷 만들기: 이름 `playledger-backups`, 위치 자동, 저장 공간 클래스 **표준**(Infrequent Access는 최소 30일 과금이라 14일 보관에 손해). 공개 개발 URL · 사용자 설정 도메인은 켜지 않는다(기본이 비공개)
   - 버킷 → 설정 → 객체 수명 주기 규칙: 접두사 `playledger-`, **14일 뒤 삭제**. `play-backup`도 R2에서 14일 지난 사본을 지우지만, 서버가 사라져도 사본이 개인정보 안내의 기한을 넘기지 않게 하는 안전장치다
   - R2 → API 토큰 관리 → **Account API 토큰 생성**(사용자 토큰이 아니라 계정에 붙는 토큰. 일반 "계정 API 토큰" 메뉴에서 만들면 S3 키가 안 나온다): 권한 **객체 읽기 및 쓰기**, 버킷 **`playledger-backups`만**, 기한 없음. 액세스 키 ID · 비밀 액세스 키와 S3 주소(`https://<계정 ID>.r2.cloudflarestorage.com`)가 한 번만 보인다. 화면을 캡처하지 않는다. 값은 Bitwarden "API 키" 폴더의 "Cloudflare 계정 API 토큰" 보안 메모(마스터 비밀번호 재확인 켬)에 둔다 ─ 내가 쓰는 API 키와 달리 서버가 쓰는 열쇠라 따로 뒀다. 회사 PC는 웹 금고만 잠깐(전역 설정 "계정 보안") ─ 서버가 사라지면 새 서버에 다시 넣어야 한다

2. **PC → 서버** (저장소 폴더):

```powershell
scp deploy/r2.env.example deploy/play-backup deploy/play-release deploy/play-restore play:~/
```

3. **서버** ─ 값은 nano로 넣고 화면은 캡처하지 않는다(4장):

```bash
sudo apt-get install -y rclone        # Ubuntu 24.04는 1.60.1 ─ 이 버전으로 시험했다
sudo install -m 600 ~/r2.env.example /etc/playledger/r2.env
sudo nano /etc/playledger/r2.env      # ENDPOINT · ACCESS_KEY_ID · SECRET_ACCESS_KEY 세 줄만
sudo grep -c '=$' /etc/playledger/r2.env    # 빈 값 개수. 0이어야 한다
sudo install -m 755 ~/play-backup ~/play-release ~/play-restore /usr/local/bin/
rm ~/r2.env.example ~/play-backup ~/play-release ~/play-restore
sudo play-backup                      # 끝에 "[backup] R2에 올림: …"이 나오면 된다
```

Cloudflare 화면의 버킷 객체 목록에 같은 이름이 보이면 끝. 실패하면 `[backup] R2 실패: …`와 종료 코드 3이 나오고, 서버 사본은 그대로 있다.

### 3.10 Steam 게임 목록 매주 (타이머)

M9(작업 큐 · 스케줄러) 전까지 새로 나온 게임이 검색에 나오게 한다. 일요일 05:30 KST + 최대 10분. 배포 · 복구와 같은 잠금을 잡아서, 배포가 돌고 있으면 30분까지 기다린다. 반대로 미러가 도는 30초쯤 동안 배포하면 "다른 배포가 진행 중"으로 멈추니 다시 친다.

```powershell
scp deploy/play-steam-sync.service deploy/play-steam-sync.timer play:~/
```

```bash
sudo install -m 644 ~/play-steam-sync.service ~/play-steam-sync.timer /etc/systemd/system/
rm ~/play-steam-sync.service ~/play-steam-sync.timer
sudo systemctl daemon-reload
sudo systemctl enable --now play-steam-sync.timer
sudo systemctl start play-steam-sync.service   # 한 번 바로 돌려 본다 (30초쯤, 끝날 때까지 프롬프트가 안 돌아온다)
sudo journalctl -u play-steam-sync -n 5        # "받은 게임 …건 · steam_apps …행 · …초"
systemctl list-timers 'play-*'
```

## 4. 함정

- **Docker는 ufw를 우회한다.** `compose.prod.yaml`에서 포트를 여는 것은 `web`뿐이다. `db` · `api`에 `ports`를 더하지 않는다
- **요청 제한은 프로세스 메모리에 있다.** 워커를 늘리면 제한도 늘고, 재배포하면 횟수가 0이 된다 (`core/rate_limit.py`)
- **`web`의 IP 172.30.0.10을 바꾸면 `server/Dockerfile`의 `--forwarded-allow-ips`도 같이 바꾼다.** 어긋나면 모든 사용자가 한 IP로 묶인다
- **HSTS가 1년이다(2026-11-05부터).** 이 주소를 http로 되돌릴 수 없다. `includeSubDomains` · `preload`는 붙이지 않는다
- **`play-compose` · `play-backup` · `play-release` · `play-restore`와 타이머 파일(`play-*.service` · `.timer`)은 배포로 바뀌지 않는다.** `/usr/local/bin/` · `/etc/systemd/system/`에 손으로 설치한 것이다. 저장소에서 고쳤으면 3.6절 · 3.9절 2 · 3단계 · 3.10절처럼 다시 올려 설치한다(타이머는 `daemon-reload`까지)
- **R2는 rclone이 올린 직후 보내는 확인용 HEAD를 501 `NotImplemented`로 거절한다**(apt rclone 1.60.1). 파일은 올라가는데 1차 시도가 실패로 찍힌다. `play-backup`은 `--s3-no-head`로 올리고 목록(`lsf`)에서 크기를 맞춰 본다. rclone 버전이나 옵션을 바꾸면 시험 파일로 먼저 본다(5절 2026-11-06 R2 설치)
- **`/etc/playledger/r2.env`도 `.env`처럼 값이 보이게 열지 않는다.** 확인은 `sudo grep -c '=$'`로 한다
- **`.env`를 값이 보이게 열지 않는다.** 캡처로 비밀값이 나간 적이 있다(5절). 확인은 `sudo grep -c '=$' /srv/playledger/.env`로 한다
- **서버 탭과 PC 탭을 헷갈린다.** `notepad` · `git rev-parse`는 PC에서, `sudo play-compose`는 서버에서 친다. 프롬프트로 구분한다
- **DB 비밀번호는 볼륨을 처음 만들 때만 적용된다.** `.env`만 바꾸면 `InvalidPasswordError`가 난다

## 5. 실제로 한 기록

**2026-11-04 · 처음 세팅과 배포 (회사 PC)**

- 3.1 ~ 3.8절 순서대로 사용자가 직접 쳤다. Docker Engine 29.9.3 · Compose v5.7.0, Vultr 스왑 2.3GB, swappiness 10
- 첫 `play-release`(`fd07964`): 이미지 받기 → DB → 마이그레이션 6개 → 교체 → 헬스체크 4번째 통과. 인증서 Let's Encrypt, 2027-02-02까지
- 미러링 198,461건 28.8초. 그 뒤 메모리 955Mi 중 424Mi 남음, 스왑 54Mi 사용. 첫 백업 22,777바이트
- 밖에서 확인: `/library/1` 200, `/assets/x.js` 404, `/docs`에 Swagger 없음, `/api/docs` · `/api/openapi.json` 404, 로그인 안 한 API 401, http → https 308, 5432 · 8000 · 2019 닫힘
- 실제 폰(안드로이드 LTE): 가입 · 로그인 · 직접 등록 · Steam 등록(커버) · 수정 · 통계 · 계정 삭제
- 요청 제한: PC IP가 429일 때 폰 IP는 로그인 200. 로그에 서로 다른 공인 IP 둘이 찍힘
- 두 창 동시 새로고침 로그인 유지, 삭제한 계정 재로그인 거절
- 두 번째 배포(`e1e368c`): 직전 백업 → 교체. 기록과 로그인 유지(사용자 확인). 지금 운영 중인 커밋
- **사고**: `.env`를 nano로 연 화면 캡처가 대화에 올라가 DB 비밀번호 · JWT 비밀이 노출됐다. DB를 만들기 전이라 둘 다 새로 만들었고 노출된 값은 어디에도 쓰지 않는다
- **안 해 본 것**: 운영 백업으로 복구, `play-release` 되돌리기, 재부팅 뒤 자동 복구, 인증서 자동 갱신, 아이폰

**2026-11-04 · 집 PC 열쇠 추가 (집 PC)**

- 3.1절 "다른 PC를 추가할 때"를 회사 PC 없이 했다: 집 PC에서 `play_vultr`(`-C home-pc`) · `~/.ssh/config` → Vultr 웹 콘솔에 root로 들어가 공개키를 `>>`로 추가 → `tail -n 2`로 `company-pc` · `home-pc` 두 줄 확인
- 집 PC에서 `ssh play` → 호스트 지문 `yes` → `sudo whoami`가 `root`
- 접속할 때 본 것: 디스크 32.7% · 메모리 39% · 스왑 1%. "New release 26.04.1 LTS"가 떠도 올리지 않는다 ─ 12월에 AWS로 옮기며 새로 세팅한다
- 웹 콘솔은 붙여 넣기가 안 될 수 있어 키 90글자를 손으로 칠 수도 있다. 회사 PC가 있으면 `Get-Content 공개키 | ssh play "cat >> ~/.ssh/authorized_keys"` 한 줄이 편하다

**2026-11-04 · 세 번째 배포 (집 PC)**

- 집 PC에서 `ssh -t play "sudo play-release f463a1b…"`: 이미지 받기 → 직전 백업 23,838바이트 → 마이그레이션(새 것 없음) → 교체 → 헬스체크 1번째 통과. 비밀번호 보기 버튼이 들어간 버전
- 밖에서: `/api/health` 200, 로그인 화면이 불러오는 `PasswordInput-*.js`에 "비밀번호 보기" 문구가 있음
- 한 줄 명령으로 `sudo`를 부를 때는 `-t`가 있어야 비밀번호를 묻는다. 없으면 "a terminal is required"

**2026-11-05 · 네 번째 배포, `task deploy` 첫 실행 (회사 PC)**

- `task deploy`: ci 성공 확인 → passphrase · sudo 비밀번호 → 이미지 받기(api 2.0초 · web 4.9초) → 직전 백업 23,906바이트 → 마이그레이션(새 것 없음) → 교체, 세 컨테이너 Healthy → 헬스체크 1번째 통과 → `health ok`. 커밋 `53db9d7`
- 밖에서(다른 명령으로): `/api/health` 200, `{"status":"ok","database":"ok"}`. 이번 배포에 `web` · `server` · `deploy` 변경이 없어 화면 번들은 `index-Cn1qTS9J.js` 그대로
- `ssh -t`는 끝날 때 `Connection to <서버 IP> closed.`를 찍는다. 이 줄이 있는 출력을 문서로 옮길 때는 IP를 뺀다

**2026-11-05 · 다섯 번째 배포, HSTS 1년 · CSP 좁히기 (회사 PC)**

- 배포 전 운영 DB 커버 호스트: `shared.akamai.steamstatic.com` 2건뿐 ─ 새 `img-src https://*.steamstatic.com`에 모두 들어간다
- 한 줄 `ssh -t play "… -c \"…\""`를 PowerShell에서 치면 `\"`가 이스케이프가 아니라 따옴표가 끊긴다(`ParserError` · 서버 bash `syntax error near '('`). 따옴표가 겹치는 명령은 서버에 들어가서(`ssh play`) 친다
- `task deploy`로 `6af62c1` 배포(사용자). 밖에서: 응답 헤더 `Strict-Transport-Security: max-age=31536000`, CSP `img-src 'self' https://*.steamstatic.com data:`, `/api/health` ok, `/privacy`에 "어디에 얼마나 남는지" 절

**2026-11-06 · 첫 복구 리허설 (회사 PC)**

- 서버: `sudo play-backup` → `playledger-20261105T232759Z.dump.age`(24,046바이트), 바로 센 운영 개수 users 2 · games 2 · entries 2 · genres 8 · game_genres 3 · refresh_tokens 14 · alembic `8c2f4a71d9e3`
- PC: `scp`로 8개(22 ~ 23KB) 받음 → 가장 최근 것을 풀어 23,846바이트 → 빈 `postgres:18` 컨테이너에 `pg_restore --exit-on-error` exit 0 → 개수가 위와 모두 같음, `steam_apps` 0(구조만), 외래 키 6 · 인덱스 22, 사용자 · 게임과 이어지는 entries 2
- 2절 PowerShell 명령을 그대로 한 번 더 돌려 같은 결과, 내려받은 뒤 되살리고 세기까지 7초. 풀린 덤프는 지웠고 컨테이너는 `--rm`이라 남지 않는다
- PC `$HOME\playledger-backups\`에 잠긴 백업 8개가 남아 있다 ─ 이게 지금의 "서버 밖 사본"이다(손으로 받을 때만 생긴다)

**2026-11-06 · `play-restore` · R2 업로드를 내 PC에서 시험 (회사 PC, 운영은 안 건드림)**

- 운영 구성(`compose.prod.yaml` + `compose.local.yaml`, 프로젝트 `playledger-check`)을 띄우고, 서버 스크립트는 `docker:29-cli` 컨테이너에서 돌렸다. `play-compose`만 이 구성을 부르는 가짜로 바꿨고 `play-backup` · `play-restore`는 저장소 것 그대로, 자물쇠는 실제 공개키
- 정상: 계정 A 기록 2건 → 백업 → A 기록 1건 · 계정 B 추가 → 되살리기 12초 → A 2건, B 로그인 401, 지우기 전 백업 1개 생김, `/api/health` ok
- 옛 버전 백업(`471f3f2597b9`에서 뜬 덤프): 되살린 뒤 마이그레이션 `471f3f2597b9 → 8c2f4a71d9e3`가 돌고 정상
- 아무것도 안 바뀌고 멈춘 경우 9가지: 잠긴 `.dump.age` · 아무 바이트 · 잘린 덤프 · 가운데가 망가진 덤프(목차 확인이 끝까지 읽어서 잡힌다) · 터미널 없음 · `no` 답 · 배포 잠금 중 · 없는 파일 · 인자 없음. `restore` 답은 진행
- 중간에 멈춘 상태 흉내(api 멈춤 · DB 없음, `/api` 502)에서 다시 실행 → "DB가 없다 ─ 지우기 전 백업은 건너뛴다" → 정상. 처음 설계에서는 여기서 `dropdb`와 지우기 전 백업이 실패해 다시 실행할 수 없었다(사전 검증에서 발견, `--if-exists`와 DB 확인을 넣음)
- 게임 목록 다시 받기는 이 구성에 Steam 키가 없어 실패 → 안내만 찍고 끝(의도한 동작). 키가 있는 경로는 운영에서 처음 본다
- R2는 rclone `local` 백엔드로 흉내: 올림 exit 0, 20일 된 사본만 지워지고 10일 된 것 · 다른 이름 파일은 남음. 쓸 수 없는 곳 · `R2_BUCKET` 없음 → exit 3, 서버 사본 있음. 복구 중 지우기 전 백업도 R2로 올라감
- Ubuntu 24.04 apt rclone **1.60.1**에서 같은 시험 + `r2.env.example` 그대로(Cloudflare provider)에 닿지 않는 주소 → 1초 만에 exit 3. 처음엔 재시도로 2분 넘게 붙잡혀서 `--contimeout 10s --low-level-retries 3`을 넣었다
- `shellcheck` 4개 파일 통과. 시험 컨테이너 · 볼륨은 지웠다

**2026-11-06 · R2 설치와 첫 업로드 (회사 PC, 서버 명령은 사용자)**

- Cloudflare: 버킷 `playledger-backups`(APAC · 표준 · 공개 URL 꺼짐), 수명 주기 규칙 `playledger` / 접두사 `playledger-` / 14일 후 삭제, 계정 API 토큰 `playledger-backup`(객체 읽기 및 쓰기 · 이 버킷만 · 무기한 · IP 필터 없음)
- 서버: apt rclone `1.60.1+dfsg-3ubuntu0.24.04.6`, `r2.env` 빈 값 0, 스크립트 3개 설치
- 첫 `sudo play-backup`: 24,046바이트 → `Failed to copy: NotImplemented … status code: 501` → `Attempt 2/3 succeeded` → "R2에 올림". `lsl`에 24046 · 원본 시각 그대로
- 시험 파일 `-vv --retries 1`: 5B 100% 보낸 뒤 501, 뒤이은 `deletefile`은 성공(파일은 생겼다). 옵션 비교: 없음 FAIL · `--s3-no-head` **OK** · `--s3-disable-checksum` FAIL · `--s3-use-presigned-request` FAIL · `--s3-upload-cutoff=0` FAIL
- `play-backup`에 `--s3-no-head` + `lsf` 크기 확인(`bfea511`). 로컬 Ubuntu 24.04 컨테이너에서 정상 exit 0 · 크기 다름 · 목록에 없음 · `lsf` 실패 · 쓸 수 없는 곳 exit 3, shellcheck 통과
- 다시 설치 뒤 `sudo play-backup`: `ERROR` 줄 없이 "R2에 올림: playledger-20261106T034102Z.dump.age (24046 바이트, 크기 확인)", `lsl`에 2개
- 14일 정리(`delete --min-age`)는 에러 없이 돌았지만, 실제로 지워지는 것은 11-20 이후에 처음 본다

**2026-11-06 · 재부팅 뒤 자동 복구 (회사 PC, 사용자)**

- 전: `up 1 day, 20:36`, api · web Up 12분(배포 직후), db Up 44시간
- `sudo reboot` 04:12:23 UTC → 04:13:37 SSH 접속 → `up 1 min`. `uptime` 감시(07 · 37분)와 백업 타이머(04:30 KST)를 피한 시각
- 뒤: api · db `Up About a minute (healthy)`, web `Up`(web은 헬스체크가 없다 ─ api는 Dockerfile, db는 Compose에 있음). `/api/health` `{"status":"ok","database":"ok"}`. 타이머 다음 실행 11-06 19:38 UTC(04:38 KST, 지연 무작위 10분), 지난 실행 11-05 19:32 UTC. 스왑 `/swapfile` 2.3G, ufw active
- 인증서(PC에서 `openssl s_client`): Let's Encrypt YE1, 2026-11-04 ~ 2027-02-02
- 로그인 안내에 "26.04.1 LTS 있음 · 업데이트 1개 · ESM 4개"가 떴다 ─ 24.04는 2029년까지 지원이라 이사(12월) 전에는 올리지 않는다
