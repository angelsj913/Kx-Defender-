# Self-Built Only Law (Kx-Defender)

**등급**: 제품 불변 조건 (PRD / 아키텍처 / 구현 모두 준수)

## 규칙

1. **외부 보안 프로그램/바이너리를 가져오지 않는다.**  
   금지 예: Impacket, Aircrack-ng, Hashcat, John, Havoc, Sliver, Cobalt Strike, ZAP, Burp, Garak, ROADtools, GraphRunner, Mimikatz, BloodHound, Nuclei, Metasploit, Nmap 패키지 연동 등.
2. **외부 도구를 wrap/shell-out/포크해서 “우리 기능”처럼 보이게 하지 않는다.**
3. **기능 아이디어의 유일한 외부 참조**는 사용자가 지정한 스킬 목록(개념/워크플로)뿐이다.  
   스킬 이름 = 구현해야 할 **능력의 이름**이지, 그 스킬 레포나 원본 도구를 설치하라는 뜻이 아니다.
4. **모든 엔진은 Kx-Defender 코드로 직접 작성**한다 (프로토콜/파서/스캐너/리스너/탐지 로직).
5. **SaaS API 키 호출로 핵심 기능을 대체하지 않는다** (third-party LLM SaaS/third-party LLM SaaS 등).

## 허용

- OS·언어 런타임 (Windows API, Python 표준 라이브러리)
- 직접 작성한 모듈/픽스처/규칙 포맷 (`KxSig`, `KxRule` 등)
- 테스트용 최소 개발 의존성 (예: pytest) — **런타임 제품 기능에 외부 보안 도구 포함 금지**

## 검증 질문 (매 PR)

- 이 변경이 외부 보안 바이너리/레포를 실행·번들하는가? → 있으면 **거부**
- 사용자가 준 스킬 개념을 **우리 코드로** 재구현했는가? → 아니면 **거부**
- 명령 표면이 KxLang인가, 외부 도구 이름인가? → 외부 도구 이름이면 **거부**
