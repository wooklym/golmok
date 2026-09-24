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

## 기준선 — 빈 L_Dev (2026-09-24, PC 세션)
스파이크 수치와 비교할 바닥값이다. 사진 콘텐츠 없이 엔진 설정(Lumen·VSM·Nanite·TSR)만의 비용을 잰다.

- 기기: 사용자 PC(Ryzen 5 7500F, 32GB, RTX 5060 8GB, 드라이버 591.86), UE 5.8.3, DX12 SM6.
- 방법: `UnrealEditor.exe Golmok.uproject /Game/Golmok/Maps/L_Dev -game -RenderOffscreen -ResX=… -ResY=… -ForceRes -csvCaptureFrames=3000 -ExitAfterCsvProfiling` → `golmok-perf`(시작 2초 제외). 창 없이 렌더하므로 백그라운드 제한을 받지 않는다. CSV 메타데이터 `systemresolution`으로 해상도를 확인했다.
- 설정[확인: 로그]: TSR(`r.AntiAliasingMethod=4`), 화면 비율 기본(`r.ScreenPercentage.Default.Desktop.Mode=1`), 동적 해상도 끔, VSync 끔.
- 장면: 캐릭터가 PlayerStart에 서 있고 골목 쪽을 본다(이동 없음).

| 구성 | 프레임 | 평균 fps | 1% low fps | 프레임 p50 ms | p99 ms | Game ms | Render ms | GPU ms |
|---|---|---|---|---|---|---|---|---|
| L_Dev 1920×1080 | 2999 | 158.5 | 133.0 | 6.26 | 7.52 | 1.75 | 6.98 | 5.99 |
| L_Dev 2560×1440 | 2999 | 127.6 | 111.0 | 7.79 | 9.01 | 1.75 | 8.57 | 7.50 |

- 1080p에서는 렌더 스레드(CPU 6코어)가 GPU보다 느리다. 무거운 장면에서는 GPU(VRAM 8GB)가 먼저 병목이 될 것으로 예상한다[추정].

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
