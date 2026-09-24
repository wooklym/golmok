# 08. 스파이크 1.1 결과 — 환경 표현 방식 비교 (템플릿)

상태: **측정 전.** 홈 Zone 골목 촬영(1.0f)과 PC 빌드 검증(1.0b)이 끝나면 채운다. → 결과로 **D-010**을 결정한다.

## 조건 (모든 경로에 똑같이 적용)
- 데이터: 홈 Zone 골목의 30~50m 청크 1개. 촬영 ID는 `docs/captures/INDEX.md` 참고.
- 엔진: UE 5.8.x, 같은 레벨, 같은 조명 프리셋(`golmok.lighting`: overcast_morning, clear_noon, golden_evening).
- 시점: `golmok.viewpoints`에 저장한 고정 시점 10곳. 원경 3, 중경 4, 근경(0.5m) 3곳.
- 경로: 같은 걷기 경로 60초를 `CsvProfile Start/Stop`으로 녹화하고 `golmok-perf`로 요약한다.
- 기기:
  - 사용자 PC(RTX 5060 8GB): 1080p·1440p, DLSS 켬/끔
  - (선택) 클라우드 고사양 인스턴스: 4K

## 절차
1. 레벨을 연다 → `import golmok.viewpoints as v` → 시점 10곳에서 `v.save("…")`를 실행한다(한 번만).
2. 경로마다 해당 표현만 보이게 두고 `v.capture("spike_a", presets=["overcast_morning","clear_noon","golden_evening"])`를 실행한다.
3. PIE나 패키지 빌드에서 `CsvProfile Start` → 경로를 걷는다 → `CsvProfile Stop` → `golmok-perf <csv> --label "a 1440p" --markdown`
4. 아래 표를 채우고, 스크린샷은 비교 이미지로 묶어 첨부한다. 용량이 크면 링크만 남긴다.

## 결과

### 시각 품질 (1~5점, 사용자와 함께 채점)
| 항목 | (a) 메시 Nanite+Lumen | (b) Cesium splat | (c) XGRIDS LCC | (a+c) 하이브리드 |
|---|---|---|---|---|
| 원경 | | | | |
| 중경 | | | | |
| 근경 0.5m | | | | |
| 얇은 구조물(전선·철망·난간) | | | | |
| 캐릭터 그림자가 바닥·벽에 떨어지는지 | | | | |
| 조명 프리셋 변경에 반응하는지 | | | | |
| 이음새(청크·배경·메시↔splat) | | | | |

### 성능
(`golmok-perf --markdown` 출력을 붙인다)

### 제작 비용
| 항목 | (a) | (b) | (c) | (a+c) |
|---|---|---|---|---|
| 처리 시간(재구성·학습·변환) | | | | |
| 수작업 시간 | | | | |
| 라이선스·배포 조건 | RealityScan EULA | Cesium(Apache), ion 비상업 주의 | XGRIDS 배포 조건 확인 필요 | |

## 결론 → D-010
(측정 후 작성)
