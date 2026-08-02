# Maltego Integration

kx-Defender 27개 명령어 Maltego Transform

---

## 파일

kx_maltego_transform.py (840줄) - Transform 엔진  
kx_maltego_graph.mmd - 흐름 diagram  
kx_command_mapping.csv - 메타데이터  
KX_MALTEGO_SETUP.md - 가이드  
test_kx_maltego.py - 테스트 (24/24)  
install_maltego_transform.ps1 - 설치  

---

## 실행

```bash
python kx_maltego_transform.py roast
python test_kx_maltego.py
.\install_maltego_transform.ps1
```

---

## 명령어 (27개)

Attack (7): roast relay loot bait breach crack nexus  
Defense (10): sentry trace audit harden triage comply forge sig watch kill  
Infrastructure (4): graph probe sweep  
Utility (7): lexicon lang update help exit

---

**상태**: Production Ready (2026-08-02)
