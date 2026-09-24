# 01. 서울 3D 베이스맵 데이터 소스 비교

조사일: 2026-09-24
표기: **[확인]** 원문 URL에서 직접 확인 / **[2차]** 기사·블로그로만 확인 / **[미확인]** 원문 확인 불가 / **[추정]** 확인된 사실에 근거한 해석(법률 자문 아님)

> 조사 환경의 한계: vworld.kr(연결 거부), Overpass API에 접근할 수 없었다. 그래서 **V-World 이용약관 원문과 OSM 서울 높이 태그 통계는 [미확인]**이다. Phase 1 착수 전에 직접 확인해야 한다(아래 "추가 확인" 참고).

## 요약

- **게임에 번들·재배포할 수 있고 라이선스가 가장 깨끗한 조합**:
  - **GIS건물통합정보**(국토부, 공공누리 제1유형, 건물 폴리곤 + 높이·층수)로 **LOD1 압출 모델**을 만든다.
  - 지형과 바닥 텍스처는 **국토지리정보원 DEM·정사영상**("이용허락범위 제한 없음")으로 채운다.
- **텍스처 실사급 서울 전역 모델은 S-Map이 유일**하다. 다만 공개 다운로드도 명시적 상용 라이선스도 없어서 **서울시와 개별 협의**가 필요하다.
- **Google Photorealistic 3D Tiles는 서울에 3D 메시가 없고**(2024 기준 평면 항공영상만 있음), 약관상 캐싱·추출·파생·오프라인이 금지된다. → **부적합**.
- **Cesium ion** 스트리밍은 조직 외부 제품에 통합하려면 별도 통합 라이선스가 필요하다. 한국 전용 데이터도 없다.
- **OSM**은 ODbL이다. 쓸 수는 있지만 다른 데이터와 결합하면 share-alike 의무가 생긴다. 서울 높이 태그 완성도도 불확실하다.

## 비교표

| 소스 | 품질/LOD | 서울 커버리지 | 포맷 | 대량 다운로드 | 게임 상업 이용 | 비고 |
|---|---|---|---|---|---|---|
| **S-Map (Virtual Seoul) / 오픈랩** | 텍스처 3D. 박스형부터 실내 표현 정밀형까지 4유형, 약 60만 동 [확인] | 서울 전역 605㎢ [확인] | [미확인] (오픈랩은 뷰어·API 방식) | 공개 경로 없음. 개별 신청으로 보임 [추정] | **협의 필요**. 데이터 자체 라이선스 [미확인] | 보안지역 처리 쟁점 |
| **V-World 3D** | LoD1 전국, LoD3~4는 주요 도심 [2차] | 있음 | xdo(자체 바이너리) | **불가**. 2019년 3D 오픈API 폐쇄(보안규정상 복제·출력 제한) [2차] | 스트리밍 API는 "이용허락범위 제한 없음"으로 표기 [확인]. 저장·추출은 사실상 불가 [추정] | 약관 원문 [미확인] |
| **GIS건물통합정보** (국토부) | 2D 폴리곤 + 높이·층수 → LOD1 생성 | 전국 약 666만 건 [확인] | SHP | **가능** (V-World/data.go.kr) [확인] | **가능. 공공누리 제1유형(출처표시)** [확인] | 최우선 후보 |
| 건축물대장 API (건축HUB) | 표제부 높이·층수 | 전국 | API | 개발계정 1만 건/일, 운영계정 확대 [확인] | "이용허락범위 제한 없음" [확인] | 보조 |
| **NGII DEM / 정사영상** | DEM 5m, 정사 12cm(도시) | 전국 | IMG / TIFF | 가능(로그인) [확인] | "이용허락범위 제한 없음" [확인] | 보안시설 처리 여부 [미확인] |
| **OpenStreetMap** | 풋프린트. 높이 태그 불균일 | 있음. 완성도 [미확인] | PBF 등 | 가능 | 가능. **ODbL**(표기 필수, 결합 DB는 share-alike) [확인] | 공공누리 1유형과의 호환성 [미확인] |
| **Google Photorealistic 3D Tiles** | 최고 품질 포토그래메트리 | **서울은 평면 영상만 있음** [확인, 2024-10 Cesium 포럼]. 2026 변화 [미확인] | 3D Tiles | **금지** | 스트리밍 시각화만. 캐싱·추출·파생·오프라인 금지, 로고 필수 [확인] | 2026-02 지도 반출 조건부 허가, 3D 포함 여부는 불명 |
| **Cesium ion** (OSM Buildings 등) | LOD1(OSM 기반, 높이 없으면 층당 3m 추정) | OSM과 동일 | 3D Tiles, glTF 클립 | 클립만 가능 | 스트리밍은 **외부 제품 통합 시 별도 라이선스** [확인]. Value-Added Clip은 영구 배포 가능하나 ODbL 적용 [확인] | 한국 전용 데이터 없음 [확인] |

## 1. 서울시 S-Map / S-Map 오픈랩

- **품질·커버리지 [확인]**:
  - 서울 전역 605.23㎢, 건물 약 60만 동에 교량·고가 등 시설물과 지형이 포함된다.
  - 모델은 "단순 박스형부터 실내까지 표현한 정밀 실사형까지" 4가지 유형이다.
  - 출처: https://news.seoul.go.kr/gov/archives/528155 , https://mediahub.seoul.go.kr/archives/2001139
- **제공 방식**:
  - 오픈랩은 "다운로드 받거나 가공할 필요 없이" 쓰는 뷰어·클라우드 방식이다. 인증키와 QGIS 플러그인을 제공한다 [확인] (https://openlab.eseoul.go.kr/).
  - 서울 열린데이터광장에서 "3D"로 검색하면 0건이다(2026-09-24).
  - 오픈랩 Q&A에 "3D 실외 입체모형 데이터 제공 신청" 문의가 있다. 개별 신청 방식으로 보인다 [추정].
- **라이선스**:
  - 오픈랩 저작권 정책 [확인]: "자유이용이 가능한 자료는 공공누리 제1유형 … 부착하여 개방… 공공누리가 부착되지 않은 자료들을 사용하고자 할 경우에는 … 담당자와 사전에 협의한 이후에 이용".
  - S-Map 소개 기사에 붙은 "공공누리 제4유형(상업적 이용금지+변경금지)"은 **기사 콘텐츠에 대한 표시**다. 3D 데이터 자체의 라이선스로 단정할 수 없다 [확인/주의].
- **판단 [추정]**: 게임에 쓰려면 서울시 공간정보 담당부서와 **서면 협의·계약**이 필요하다. 보안지역 처리 조건이 붙을 가능성이 크다. MVP 일정에 넣기에는 불확실성이 크므로 **병행 문의(장기 옵션)**로 둔다.

## 2. 국토부 V-World / 국토지리정보원

- **V-World 3D 건물 [2차]**:
  - LoD1은 전국, LoD3~4는 주요 도심 위주다. 포맷은 자체 `.xdo`다.
  - 2019-05 3D 데이터 오픈API가 폐쇄됐고, 이후 재개 불가 공지가 나왔다. 배경은 「국가공간정보 보안관리규정」상 3D 데이터 "복제·출력" 제한이다.
  - 출처: https://www.vw-lab.com/53
- **WebGL 3D 지도 API [확인]**: 공공데이터포털 표기는 "이용허락범위 제한 없음, 무료"다(https://www.data.go.kr/data/3073144/openapi.do). 하지만 **스트리밍 뷰어 API**라서 캐싱·저장·게임 내 재가공 허용 여부는 V-World 약관 원문으로 확인해야 한다 [미확인].
- **보안 규정**: 공개제한 공간정보 보안심사 규정(국토부고시 제2024-286호) https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulId=81219&efYd=0
- **NGII [확인]**:
  - DEM(5m, IMG)과 정사영상(TIFF, 도시 12cm)은 "이용허락범위 제한 없음", 무료, 국토정보플랫폼 로그인 후 다운로드한다.
  - 출처: https://www.data.go.kr/data/15059920/fileData.do , https://www.data.go.kr/data/15059919/fileData.do
  - NGII 3차원 공간정보 구축 사업은 확인했지만 배포 여부는 [미확인]이다(https://www.ngii.go.kr/kor/content.do?sq=205).

## 3. OpenStreetMap + 국내 높이 보강 데이터

- **ODbL 핵심 조항 [확인]** (https://opendatacommons.org/licenses/odbl/1-0/):
  - 4.3: Produced Work를 공개 사용하면 출처 고지가 필요하다.
  - 4.4(b): 상당 부분을 추출해 새 DB에 넣으면 그 DB는 Derivative Database가 된다.
  - 4.6: Derivative Database나 그로부터 나온 Produced Work를 공개하면 **DB 전체나 변경분을 기계 판독 가능한 형태로 제공**해야 한다.
- **OSMF Produced Work 가이드라인 [확인]**: "published result … intended for the extraction of the original data" → DB로 본다. 게임에 대한 명시적 판단은 없다.
- **게임 함의 [추정]**:
  - 렌더링된 게임은 Produced Work로 보는 해석이 일반적이다. 이때 필요한 것은 "© OpenStreetMap contributors" 표기다.
  - 그러나 **OSM에 건축물대장 높이 등을 결합하면 결합 DB 공개 의무**가 생긴다. 게임 파일에 원좌표 지오메트리를 쉽게 추출할 수 있게 넣으면 DB로 볼 여지도 있다.
- **서울 높이 태그 완성도**: [미확인]. 떠도는 "render_height 99.96%" 수치는 기본값을 계산한 필드라 근거가 되지 않는다.
- **GIS건물통합정보 [확인]**:
  - 국토부 데이터로, 연속지적 건물 폴리곤과 세움터 건축물대장 속성(높이·층수)을 결합했다. 전국 6,656,497건, SHP, **공공누리 제1유형**이다.
  - 출처: https://www.data.go.kr/data/15083092/fileData.do
  - 1유형은 출처만 표시하면 상업 이용과 변경이 허용된다(https://www.kogl.or.kr/info/license.do).
  - → **OSM을 거치지 않고 이 데이터로 LOD1을 만드는 것이 라이선스상 가장 깔끔하다 [추정].**

## 4. Google Photorealistic 3D Tiles

- **서울 커버리지 [확인]**: Cesium 직원이 2024-10-15 포럼에서 서울 코엑스 지역에 대해 "only contains overhead imagery for this region"이라고 답했다. 2026-09 현재 서울 3D 메시가 추가됐다는 공식 발표는 찾지 못했다 [미확인].
- **한국 지도 반출 [확인]**:
  - 2026-02-27 국토지리정보원 협의체가 1:5,000 지도를 조건부로 반출 허가했다.
  - 조건: 보안시설 블러, 국내 서버에서 가공한 뒤 정부 검수 등.
  - 3D가 대상에 포함되는지는 명시되지 않았다.
  - 출처: https://www.korea.kr/news/policyNewsView.do?newsId=148960112
- **약관 [확인]** (GMP ToS, 2026-08-26 수정본, https://cloud.google.com/maps-platform/terms):
  - 3.2.3(a): "will not export, extract, or otherwise scrape … pre-fetch, index, store, reshare, or rehost"
  - 3.2.3(b): 명시적으로 허용된 경우 외에는 캐싱 금지
  - 3.2.3(c): "will not create content based on Google Maps Content"
  - 3.2.3(e): Google 외 지도와 함께 사용 금지
- **Map Tiles 정책 [확인]** (https://developers.google.com/maps/documentation/tile/policies):
  - "non-visualization use cases … Geodata extraction or resale, Offline uses" 금지
  - 자체 3D 객체를 오버레이하는 것은 허용되지만, 그 객체가 "extracted, traced, or otherwise derived … from Photorealistic 3D Tiles"여서는 안 된다.
  - 로고 표시와 저작권 표기가 필수다.
- **판단**: 충돌 메시 생성(파생), 오프라인, 캐싱이 모두 금지된다. **Google 외 지도(우리 베이스맵)와 섞어 쓰는 것도 금지**된다. 서울에는 3D도 없다. → **채택 불가.**

## 5. Cesium ion

- **약관 [확인]** (https://cesium.com/legal/terms-of-service/, 2025-08-20 개정):
  - "does not permit you to include ion in your own solution that you make commercially available… contact us for an integration license."
  - 2.2.2: Clips를 제외하면 오프라인·로컬 저장 금지. 일반적인 클라이언트·프록시 캐싱은 허용.
  - 2.2.3: Cesium ion 로고 표시 필수.
  - **2.3 Value-Added Clips**: 더 큰 저작물에 실질적 가치를 더해 포함한 클립은 **영구 배포와 판매가 가능**하다. 게임 번들이 가능한 유일한 경로다. 단 OSM Buildings 클립에는 ODbL이 적용된다. Google 타일은 클립할 수 없다.
- **요금 [확인]** (https://cesium.com/platform/cesium-ion/pricing/):
  - Community: 무료, 비상업
  - Commercial: $149/월~
  - Premium: $499/월~
  - 모두 "Commercial use within your organization"으로 한정된다. 외부 제품에 쓰려면 문의해야 한다.
- **한국 데이터**: Global 3D Content에 일본 PLATEAU는 있지만 **한국은 없다** [확인].
- **판단**: 서울 기준으로는 Cesium OSM Buildings 이상의 가치가 없다. 그런데 이것은 OSM을 직접 쓰는 것과 같다. → **채택 불필요.** 다만 3D Tiles 변환 도구(3d-tiles-tools, 오픈소스)는 활용한다.

## 추천안

| 레이어 | 데이터 | 라이선스 | 처리 |
|---|---|---|---|
| 지형 | NGII DEM 5m | 제한 없음 | quantized-mesh 또는 heightmap 타일 |
| 지면 텍스처 | NGII 정사영상 12cm | 제한 없음 | 래스터 타일(지형에 드레이프) |
| 건물 LOD1 | **GIS건물통합정보** (높이·층수) | 공공누리 1유형 | 폴리곤 압출 → 절차적 파사드(창·층 패턴) → glTF → 3D Tiles |
| 도로·보도·녹지(선택) | 국가 도로명주소 전자지도 또는 NGII 수치지도 | 확인 필요 | 지면 폴리곤·보도 턱 |
| 고품질 구역 | **자체 촬영(splat + collision mesh)** | 자체 소유 | 구역 교체 레이어 |
| (장기) 텍스처 실사 LOD | S-Map | 서울시와 계약 | 협의 성사 시 LOD1을 대체 |

- 출처 표시(1유형)는 게임 크레딧과 로딩 화면 하단에 넣는다.
- 보안시설 처리: 원천 데이터가 이미 공개 데이터이긴 하지만, **우리가 촬영해 올리는 고품질 구역**에 대해서는 05-legal-policy.md의 필터를 적용한다.

## 추가 확인 필요 (Phase 1 착수 전)

1. **V-World 이용약관 원문**. 사람이 브라우저로 확인해야 한다.
2. **S-Map 3D 모델의 제공 절차와 라이선스**. 서울시 공간정보 담당부서(오픈랩 기술지원 02-576-2395)에 서면으로 문의한다.
3. OSM 서울 height/building:levels 태그 비율(taginfo 집계). 참고용이다.
4. 2026 반출 허가 이후 Google 3D 메시 서울 추가 여부. 참고용이며, 추가돼도 약관상 부적합하다.
5. GIS건물통합정보가 좌표 정밀도·보안시설 처리 측면에서 게임 공개에 문제가 없는지. 공공누리 1유형이므로 원칙적으로는 문제없다 [추정].

## 출처

- S-Map: https://openlab.eseoul.go.kr/ , https://news.seoul.go.kr/gov/archives/528155 , https://mediahub.seoul.go.kr/archives/2001139 , http://opengov.seoul.go.kr/sanction/9028710
- 공공누리: https://www.kogl.or.kr/info/license.do
- V-World: https://www.vw-lab.com/53 , https://www.data.go.kr/data/3073144/openapi.do , https://www.data.go.kr/data/15101109/openapi.do , https://www.etnews.com/20250115000170
- 보안심사 규정: https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulId=81219&efYd=0
- GIS건물통합정보: https://www.data.go.kr/data/15083092/fileData.do
- 건축물대장 API: https://www.data.go.kr/data/15134735/openapi.do
- NGII: https://www.data.go.kr/data/15059920/fileData.do , https://www.data.go.kr/data/15059919/fileData.do , https://www.ngii.go.kr/kor/content.do?sq=205
- ODbL: https://opendatacommons.org/licenses/odbl/1-0/ , https://osmfoundation.org/wiki/Licence/Community_Guidelines/Produced_Work_-_Guideline
- Google: https://developers.google.com/maps/documentation/tile/3d-tiles-overview , https://developers.google.com/maps/documentation/tile/policies , https://developers.google.com/maps/documentation/tile/usage-and-billing , https://cloud.google.com/maps-platform/terms , https://cloud.google.com/maps-platform/terms/maps-service-terms , https://community.cesium.com/t/google-3d-tiles-unity-south-korea-not-working/35783
- 지도 반출: https://www.korea.kr/news/policyNewsView.do?newsId=148960112 , https://zdnet.co.kr/view/?no=20260227120235
- Cesium: https://cesium.com/legal/terms-of-service/ , https://cesium.com/legal/third-party-terms/ , https://cesium.com/legal/terms-for-google/ , https://cesium.com/legal/cesium-global-3d-content-tos/ , https://cesium.com/platform/cesium-ion/pricing/ , https://cesium.com/platform/cesium-ion/content/cesium-osm-buildings/ , https://cesium.com/platform/cesium-ion/cesium-ion-self-hosted/ , https://cesium.com/blog/2024/05/08/cesium-ion-clipping/
