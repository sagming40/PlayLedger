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
| 앱 위치 | `/srv/playledger/` (`compose.yaml` · `.env` · `image.env`), 백업 `/var/backups/playledger/` |
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

**게임 목록 미러링** (서버, 약 20초 ~ 몇 분):

```bash
sudo play-compose run --rm api python -m app.scripts.sync_steam_apps
```

**백업 내려받기** (PC). 열쇠가 없으면 못 연다:

```powershell
New-Item -ItemType Directory -Force "$HOME\playledger-backups" | Out-Null
scp "play:/var/backups/playledger/*.dump.age" "$HOME\playledger-backups\"
```

**복구** (PC의 로컬 운영 구성에서 연습. 운영 복구도 같은 순서다):

```powershell
$latest = Get-ChildItem "$HOME\playledger-backups\*.dump.age" | Sort-Object Name | Select-Object -Last 1
age -d -i "$HOME\playledger-backup.key" -o "$env:TEMP\play-restore.dump" $latest.FullName
# 빈 DB에 되살린 뒤 users · games · entries 수를 운영과 대조한다. 끝나면 임시 파일을 지운다
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
scp deploy/prod.env.example deploy/play-compose deploy/play-release deploy/play-backup deploy/play-backup.service deploy/play-backup.timer play:~/
```

서버에서 설치하고 비밀값을 만든다. 비밀값은 화면 캡처 · 채팅에 내지 않는다:

```bash
sudo install -d -m 750 /srv/playledger
sudo install -m 600 ~/prod.env.example /srv/playledger/.env
sudo sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 32)/; s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" /srv/playledger/.env
sudo nano /srv/playledger/.env    # STEAM_API_KEY만 붙여 넣는다 (https://steamcommunity.com/dev/apikey)
sudo grep -c '=$' /srv/playledger/.env    # 빈 값 개수. 0이어야 한다 (값은 출력되지 않는다)
sudo install -m 755 ~/play-compose ~/play-release ~/play-backup /usr/local/bin/
sudo install -m 644 ~/play-backup.service ~/play-backup.timer /etc/systemd/system/
rm ~/prod.env.example ~/play-compose ~/play-release ~/play-backup ~/play-backup.service ~/play-backup.timer
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

## 4. 함정

- **Docker는 ufw를 우회한다.** `compose.prod.yaml`에서 포트를 여는 것은 `web`뿐이다. `db` · `api`에 `ports`를 더하지 않는다
- **요청 제한은 프로세스 메모리에 있다.** 워커를 늘리면 제한도 늘고, 재배포하면 횟수가 0이 된다 (`core/rate_limit.py`)
- **`web`의 IP 172.30.0.10을 바꾸면 `server/Dockerfile`의 `--forwarded-allow-ips`도 같이 바꾼다.** 어긋나면 모든 사용자가 한 IP로 묶인다
- **HSTS는 지금 하루다.** 운영 확인은 끝났다. 다음 배포에서 `web/deploy/Caddyfile`을 1년으로 늘린다
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
