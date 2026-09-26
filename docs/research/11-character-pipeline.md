# 11 — 캐릭터 제작 경로 조사

2026-09-26 · ChatGPT Astra · **가설/제안, 구매·발주 없음**.
목표·후보는 [캐릭터 컨셉](../design/character-concept.md), 구현 계약·D-018은 `docs/plan/WP-18-characters.md`.
가격·약관은 아래 확인일 당시 자료다. [확인]은 원문 열람, [2차]는 다른 기록 인용, [확인 필요]는 원문 접근/조건 확인이 남았음, [미확인]은 추정이다.

## B1. 공통 기술 사양 (제작 목표)

고사양 화면 품질부터 정한다. RTX 5090 4K DLSS Quality 60fps, 4070 Ti급 1440p DLSS Quality 60fps가 목표이고, RTX 5060 8GB 1080p 30fps는 LOD·스케일러빌리티 하한이다. 아래 예산은 **측정값이 아닌 발주 기준 가설**이다. 캐릭터 한 명의 정면 0.5m·포토 모드 고해상도에서도 눈꺼풀·입·손·봉제선 실루엣이 유지되어야 한다.

| 항목 | 높은 품질 기준 | 하위 단계 |
|---|---|---|
| 삼각형(몸+옷+헤어+휴대 소품 합계) | LOD0 100k~140k, 얼굴/손 우선. 스컬프 원본은 제한 없음 | LOD1 60k, LOD2 30k, LOD3 12k. 화면 점유율을 기준으로 전환, 얼굴 모프 유지 여부 검수 |
| 재질 | 피부/몸, 의상, 헤어, 눈, 소품: 최대 5개 슬롯. Opaque 중심, 필요할 때만 Masked | 머티리얼 슬롯을 LOD에서도 줄임. 전신 1개 atlas는 얼굴 근접 품질을 해치면 금지 |
| 텍스처 | 얼굴/몸 4K 세트 1, 옷 4K 세트 1, 헤어 2K, 눈/소품 2K 공유. BaseColor(BC7), Normal(BC5), ORM(BC7), 선택 마스크 | 5060에서는 2K/1K mip 제한. 8K는 0.5m 비교에서 차이가 확인된 단일 얼굴만 재승인 |
| 뼈 | V-08 채택 스켈레톤의 이름·축·계층 보존. 목표 총 deform 160 이하, 보조 8~16, vertex influence 4 기본/8 예외 | LOD2부터 손가락·보조 뼈 축소, 스키닝/애니메이션 CPU·GPU 비용 별도 기록 |
| 표정 | blink L/R, smile L/R, frown, surprise, jawOpen, cheek 등 16~24 모프. 턱/안구 뼈, 관통 보정 corrective 4~8 | 얼굴 모프 델타의 버텍스 수 기록, 멀리서는 표정 평가 빈도/LOD 축소 |
| 머리카락 | 짧은 단발은 실루엣을 조형한 불투명 헤어 덩어리+소량 카드. 스타일상 원하는 모양을 우선 | 고사양 그룸 비교 샷은 가능하나 첫 캐릭터의 짧고 덩어리진 스타일에는 카드/조형 메시를 권장. 그룸을 단순 비용 이유로 배제한 것은 아님 |
| 옷·부속 | 몸통은 스킨, 가방 끈/짧은 옷단은 8~16 보조 뼈. 긴 치마·코트가 생기면 Chaos Cloth 별도 예산 | 5060에서는 보조 뼈 애니메이션으로 대체, 사진 정지 시 튀는 물리 상태 확인 |

**VRAM 계산 예**: 4K BC7/BC5는 각 16 MiB(최상위 mip), 전체 mip 약 ×4/3. 4K 세트 두 개 ×3장 = 약 128 MiB, 2K 세트 두 개 ×3장 = 약 32 MiB. 텍스처 약 160 MiB + 메시/스키닝/모프/버퍼 40~100 MiB를 잡아 캐릭터당 **200~260 MiB 목표**, 그룸 제외. 그림자·Lumen 공유 버퍼와 엔진 전체 VRAM은 이 숫자에 포함하지 않는다. 저사양 mip 제한 시 텍스처 약 40 MiB, 총 80~140 MiB를 가설로 측정한다. 교체 순간 구/신 에셋이 동시에 상주할 수 있으므로 피크 VRAM도 기록한다.

납품 검수는 동일 카메라에서 LOD0/1 스냅샷, 모프 최대치 조합, 손-머리/배 간섭, 25cm 계단, 180도 턴, 그림자, 4 프리셋을 포함한다. 폴리곤 수만 맞는 납품은 통과가 아니다.

## B2. 경로 비교

### 품질·비용·기간·리깅

기간/작업시간은 **[미확인: 계획 추정]**이며 업체 약속이 아니다. 별도 표시가 없는 계획 비용은 USD, 세금·플랫폼 수수료·환율 제외다. Fab/Meshy는 아래 한국어 UI의 원화 표시를 그대로 기록했다. 실제 돈 지출은 D-018 ② 후 소유자가 결정한다.

| 경로 | B1 충족 가능성과 작업 | 공개 비용 근거 / 계획 비용·기간 | 스켈레톤 | 리스크 |
|---|---|---|---|---|
| **(a) 인간 아티스트 외주 — 권장** | 얼굴·실루엣·표정·옷감까지 원화부터 맞춤 제작, B1 납품 계약 | [확인] [Upwork 요율](https://www.upwork.com/hire/3d-modelers/cost//): “$17–$30/hr.” 일반 3D 모델러 표본이며 고품질 캐릭터 견적 아님. [미확인] 160~280h에 단순 적용하면 $2,720~8,400, 4~7주. 숙련 아티스트·IP 양도 비용은 더 높을 수 있음 | 발주 시 V-08 채택안으로 지정, IK Retargeter 납품. UE 마네킹과 UEFN_Mannequin을 같은 것으로 취급하지 않음 | 원화/얼굴/리그 전문성 편차, 저작권·수정 범위 계약 필요 |
| (b) Fab 구매 | [확인] [Minimal Casual Man](https://www.fab.com/listings/960de700-1d7d-4e9f-a4ed-74bb4bcefca6) 판매자 페이지: 스타일라이즈드 남성, 의상3·클립10·헤어 카드. B1 모프/LOD 충족은 [미확인] | [확인] 2026-09-26 한국 가격 선택 UI: 개인용 ₩29,790(VAT ₩2,708 포함), 기업용 ₩44,690(VAT ₩4,063 포함). 페이지 일반 세금 안내와 선택 UI가 달라 최종 주문액 재확인. 적응40~100h/1~3주 가설 | [확인: 판매자 주장] UE4 Mannequin-compatible 계층+턱/눈 뼈, 자체 reference pose. UE5 Manny는 IK Retargeting 필요. 실제 UE5.8.3/UEFN 호환은 미검증 | [확인] AI 사용 허용 ‘아니요’, AI 생성 ‘아니요’. 이미지/스크린샷을 AI에 입력하지 않음. 고유 IP 약함·원본 공개 불가 |
| (c) AI 3D (Meshy) | 초기 볼륨·턴어라운드 실험. 관절 토폴로지·손·모프는 인간 재작업 전 B1 미달로 취급 | [확인] [가격 페이지](https://www.meshy.ai/ko/pricing), 2026-09-26 브라우저 월간 선택: Free ₩0·월100 credit, Pro 월₩28,869·월1,000 credit. 신규 첫 달50% 프로모션 ₩14,435는 정가와 구분. 세금/최종 청구액은 [확인 필요]. 최종 제작80~200h/2~5주 가설 | 자동 리그가 UE/UEFN과 같다는 근거 없음. 수동 리그 또는 IK Retargeter | 학습/권리·유사 출력·숨은 뒤면·UV/관절 수정 비용 |
| (d) VRoid/VRM + VRM4U | 사람형 얼굴·의상 프로토타입은 빠름. 4.5등신·PBR 의상·고유 표정/LOD는 별도 제작 | [확인] [VRoid Studio](https://vroid.com/en/studio) 무료 도구. [미확인] 맞춤 작업 60~160h/2~4주 | VRM 휴머노이드 → VRM4U → retarget chains; MToon에서 PBR 룩 변경 필요. 5.8.3 플러그인 빌드 미검증 | 프리셋 권리, 외부 BOOTH 에셋별 라이선스, 생성/모델 내보내기 UI 제약 |
| (e) MetaHuman | 실사 얼굴/표정 품질은 강함. 135cm 4.5등신 목표는 상당한 재조형·리그 검수 필요 | [확인] [MetaHuman license](https://www.metahuman.com/license): “under $1 million USD in revenue” 무료 범주 설명. UE 계약의 게임 로열티 조건은 별도. [미확인] 스타일 수정 80~240h/2~6주 | MetaHuman rig → V-08 소스 IK Retargeter. 고급 얼굴 rig를 무조건 가져오면 예산 초과 | 실사 얼굴이 귀여운 비율과 충돌, DNA/파생 콘텐츠·AI 금지 조건 확인 |
| (f) AI 초안 + 인간 리토폴로지/리깅 | 실루엣은 빨리 보나 사람의 독자적인 표현 작업이 빠지면 B1·IP 목표 미달 | (a)의 공개 시간 요율을 참고. [미확인] 120~240h + 도구 비용, 3~6주. AI 때문에 싸다고 단정하지 않음 | 인간이 최종 스켈레톤/스킨과 retarget asset을 다시 제작 | AI 출력 조건이 리토폴로지 후 사라지지 않음. 수정만으로 저작권이 자동 확보되지 않음 |

### 라이선스·원본 공개·한국 사용

조건별 원문 확인일 2026-09-26. 문의·가입·구매·약관 동의는 하지 않았다.

| 경로 | 상업/소유권·학습·결합/지역 | 공개 저장소 |
|---|---|---|
| 외주 | 계약 미체결이므로 권리 없음. [확인 필요] 상업 이용·전세계(한국 포함) 배포·수정·2차적저작물작성권·소스 제공·협업자 공유·AI 고지의 명시적 계약. 학습용 업로드와 포트폴리오 공개는 사전 허가 조항으로 제한하는 안 | 계약상 허용이어도 원본은 비공개 기본. 공개 코드 라이선스를 에셋에 자동 적용하지 않음 |
| Fab | [확인] [공식 요약](https://www.fab.com/eula): “Use the assets commercially or privately”. 요약은 비구속적이라고 명시. [2차: V-08 PC 세션 기록, 소유자 재확인 전] Fab EULA §5(a) 원본 공개 제한, §6(a) GPL/LGPL(동적 예외)/CC-BY-SA 결합 금지, §6(b)(vii) NoAI. 전체 계약이 웹 추출에서 빠져 [확인 필요]. 한국 사용/제재·상품별 UE-only 여부도 구매 전 원문 확인 | **원본 커밋 금지**. 협업자만 비공개 공유. NoAI 에셋/스크린샷은 프로젝트 규칙상 어떤 AI 입력에도 금지 |
| Meshy | [확인] [Terms 2026-09-19](https://www.meshy.ai/terms-of-use) §2.9: “from non-Enterprise Customers to train”; §3 유료 출력 소유·무료 CC BY 4.0, Service Assets는 출력에 필요한 범위의 worldwide 허락. 비기업 학습 허락과 가격 FAQ의 ‘동의 없이 학습 안 함’이 충돌하므로 별도 계약 없는 초안 업로드 비권장. §2.4 생성 표시 제거 금지. 사전 학습 데이터 전체 목록/한국 서비스 접근·제재 적용은 [확인 필요]. GPL식 결합 조건과 동일하다고 추정하지 않음 | 유료 Output과 Service Assets를 분리해야 하며 일괄 원본 공개 허용으로 해석하지 않음. 최종 경로로 채택 안 함 |
| VRoid/VRM | [확인] [공식 가이드](https://vroid.com/en/studio/guidelines): “not CC0”. 특별 조건 없는 프리셋의 상업 사용/수정/판매를 허용하지만 pixiv 권리는 유지. 모델 생성·출력 앱은 별도 허락 필요. 이용약관 11조 링크는 본문 접근 실패 [확인 필요]. 한국 제한/AI 학습 허락을 추정하지 않음. VRM 파일별 이용허락도 검사 | 단순 공개 게임 선택 기능과 사용자 모델 내보내기는 구별. 원본 공유는 프리셋/외부 아이템/VRM 메타별 확인 전 보류 |
| VRM4U 코드 | [확인] [LICENSE](https://github.com/ruyo/VRM4U/blob/master/LICENSE): “MIT License”. 고지 유지, 상업 이용 가능. 번들 third-party·모델 데이터 조건은 별도. 한국 제한은 이 MIT 문구에서 발견 안 됨 | 플러그인 MIT 코드와 VRM 에셋은 별개. 이번 PR에는 플러그인 추가 안 함 |
| MetaHuman/UE | [확인] [UE EULA §6(c)](https://www.unrealengine.com/eula/unreal) 결합 금지 목록: “GNU General Public License (GPL), Lesser GPL (LGPL)”; 동적 LGPL 예외와 CC-BY-SA도 확인. MetaHuman 라이선스 안내는 UE 표준 계약 적용. AI 학습 사용/메타휴먼 원본 공유·국가 제재 조건은 계약 전체와 해당 에셋 조항 확인 필요 | 소유한 독립 원화와 엔진/MetaHuman 파생 파일 구별. 생성했다는 이유로 원본 공개하지 않음 |

OpenAI 컨셉 출력 및 한국/미국 저작물성·국내/Steam 표시의 근거는 [A5](../design/character-concept.md#a5-권리-점검)에 있다. 모든 경로에서 NC·AGPL 도구는 제외한다. 이 표는 승인된 새 의존성 목록이 아니다.

## B3. 저장·배포

**권장: 소유자가 관리하는 비공개 에셋 저장소 + LFS**. 역할별 접근을 주고 tag/version·SHA256·계약/영수증 위치·원본 출처 manifest를 보관한다. 공개 repo에는 경로/버전/해시 및 복사 절차만 둔다. Claude/Astra 공유는 계약이 허용한 협업자 범위에서만 한다.

PC 로컬+복사 스크립트는 시작이 쉽지만 PC 장애·버전 불일치·다른 worktree에서의 재현 누락이 생기기 쉽다. ①/V-11의 템플릿 마네킹에는 기존 `tools/ue/add-mannequin.ps1`만 사용한다. ② 이후 에셋 동기화 도구는 별도 작업으로 만들고 다운로드 동의/결제를 자동화하지 않는다.

- 로컬 Content 규약: `/Game/Characters/Golmok/<character_id>/v01/{Meshes,Materials,Textures,Anims,Rig}`. 파일은 `SK_<id>`, `ABP_<id>`, `IK_<id>`, `RTG_<source>_<id>`.
- 소유권 없는 Fab 원본은 `/Game/Characters/Vendor/<pack>/...` 아래 두고 원본 레이아웃을 보존한다. 변환 사본도 같은 ignore 트리 안에 둔다.
- [확인: 저장소] `.gitignore`의 `unreal/Golmok/Content/Characters/`가 전체를 제외한다. `Content/Golmok/Characters/`는 이 규칙 밖이므로 쓰지 않는다.
- Config JSON은 기존 UFS `../Config/Golmok`가 포함한다. **JSON의 soft path만으로 메시가 cook되지는 않는다.** 18a는 에디터/PC 테스트 범위이며 패키징 검증은 별도. 18b에서는 승인된 에셋의 AssetManager/PrimaryAssetLabel 또는 AlwaysCook 규칙을 검토하고 패키지로 확인한다.
- docs 컨셉 JPG(1600px 이하)는 별도 허용된 공개 자료이며 로컬 `git lfs`로 커밋한다. 원본 3D 에셋과 혼동하지 않는다.

## B4. UE 5.8 기술 세부

확인일 2026-09-26. 엔진 소스 수정 없이 가능한 범위이며 **기능 존재와 Golmok 납품 합격을 구별**한다. 아래에서 채택하지 않은 플러그인을 설치하거나 .uproject에 켜지 않았다.

| 항목 | 공식 근거와 확인 범위 | c01 제작/검수 방침 |
|---|---|---|
| IK Rig·IK Retargeter | [확인] [IK Rig Retargeting](https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine): 서로 다른 뼈 수·이름·방향을 가진 리그 사이 전송, 손/발 IK 정렬. 소스/타깃 체인과 retarget pose가 필요 | V-08 소스 확정 → pelvis/root·팔/다리 체인 → A/T pose 정렬 → 손-머리 여유·발 평면/발가락 → 루트 이동량/접지 프레임 순서. 18a는 같은 스켈레톤 ABP만 허용하며 리타깃 코드를 넣지 않음 |
| 5.8 리타깃 보강 | [확인] [5.8 릴리스 노트](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes), Foot Definition / Retarget Override Sets. 짧은 캐릭터의 골반 수직 움직임 제어·발 평면/발가락 정의·op 순서 보강 | 135cm/4.5등신 프록시의 계단·턴에 V-08 추가 시험. Override Set으로 캐릭터별 보정을 관리할 수 있는지 확인. 엔진 기능 소개의 결과를 자동 합격으로 옮기지 않음 |
| Mutable 5.8 | [확인] 같은 릴리스 노트 Mutable 절: “reaches production readiness”. Dataless 객체·메시 단위 작업·생성 처리 개선 | 기능 성숙도는 확인했으나 우리 의상 조합 품질/생성 지연은 미측정. 첫 1종에는 필요 없음. 18b 이후 의상·체형 조합 수 증가 시 단순 모듈 메시와 메모리/전환 hitch/cook 크기를 비교해 도입 |
| 그룸·카드 | [확인] [Groom Scalability](https://dev.epicgames.com/documentation/en-us/unreal-engine/groom-scalability-and-performance-with-unreal-engine): “Strands geometry offers natural hair motion and looks”. strand/card/mesh를 LOD와 플랫폼에 따라 전환 가능. 곡선/점 수와 시뮬레이션·보간·voxelization 비용 | 짧고 명확한 덩어리 단발에는 조형 메시+소량 카드 권장. 긴 부드러운 잔머리가 룩에 필요하면 5090 근접 groom A/B를 먼저 촬영. 5060에서는 카드/메시 LOD, 눈썹/속눈썹 Masked 경계와 DOF·그림자 별도 검사 |
| 스켈레탈 Nanite·LOD | [확인] [Nanite](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine), Skeletal Mesh 절: “No geometry LODs”; animation LOD와 VSM 그림자 지원을 명시. [확인] [콘텐츠 지침](https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content)은 겹친 면·카드 같은 aggregate의 overdraw를 경고 | 지원 안 된다고 단정하지 않는다. **첫 납품은 일반 스켈레탈 LOD0~3**를 필수로 확보하고, Nanite 고밀도 사본을 추가 비교. 얼굴 모프·cloth·보조 변형·재질 조합의 5.8.3 실제 호환성은 [확인 필요]. 이 문서의 지원 목록만으로 전부 지원이라고 추정하지 않음. 모프/눈꺼풀 품질을 포기하며 Nanite를 쓰지 않음 |
| Chaos Cloth | [확인] [Clothing Tool](https://dev.epicgames.com/documentation/en-us/unreal-engine/clothing-tool-in-unreal-engine): “particle simulation”. 에디터에서 cloth 자산을 만들고 메시 section에 할당하는 흐름 | 짧은 재킷은 skin+보조 뼈로 모양부터 통제. 긴 옷은 낮은 해상도 sim mesh/충돌체·iteration·self-collision·teleport reset을 별도 설계. 사진 진입 time dilation과 숨김/복귀, 벽에 기대기, 순간 교체 시 폭발·튀는 옷단 검수 |
| 보조 뼈 비용 | [확인] 5.8 릴리스 노트에 Control Rig Dynamics와 사용하지 않는 뼈 축소 도구 소개. 프로젝트에서의 ms 절감은 [미확인] | 보조8~16개, influence4 기본, 멀리서 평가 줄이기. CPU 애니메이션과 GPU skin 비용을 나눠 기록. 릴리스 노트의 비교 배수를 Golmok 예상치로 쓰지 않음 |
| 귀여운 표정 | [확인] [FBX Morph Target Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-morph-target-pipeline-in-unreal-engine)의 모프 가져오기 경로와 5.8 릴리스 노트의 Skeletal Editor Blendshape Rigging Tools | 16~24개 수동 모프+턱/안구 뼈를 권장. 근접 미소/눈감음/놀람을 아티스트가 직접 조형하고 4~8 corrective로 눈꺼풀·볼 관통 보정. ARKit52/MetaHuman 얼굴 전체를 비용 때문에가 아니라 필요한 표현 범위와 형태 통제 기준으로 비교. Live 얼굴 캡처는 이번 범위 밖 |

**검증 순서**: 일반 LOD/PBR 기준 샷 → retarget+표정 조합 → 헤어 방식 → 천/보조 뼈 → Nanite 별도 사본 → 포토 모드. V-12에서 확정할 PBR·5.8 Toon BSDF·장난감 재질의 광 반응은 [A1](../design/character-concept.md#a1-아트-디렉션-가설)에 모았다. 실험 기능 때문에 공유 렌더 설정이나 엔진 소스를 수정하지 않는다.

**프레임 예산 가설**: 60fps 전체16.67ms 중 캐릭터1종 추가분을 GPU1.5ms·게임스레드0.5ms 이내에서 먼저 검토하되, 피부/머리 품질 손실이 크면 다른 항목 최적화와 함께 다시 배분한다. 5060은 전체33.33ms·8GB 한도와 peak VRAM을 확인한다. LOD/그룸/cloth 각각 on/off 동일 구도200프레임 비교, 첫 로드 hitch 별도 기록. 다른 UE 프로세스가 돌면 측정하지 않는다. 이 숫자는 엔진 실측/납품 보증이 아니다.

## B5. 결론과 승인 단계

**제작 경로는 (a) 인간 아티스트 외주를 권장한다.** AI 컨셉은 방향을 설명하는 자료로만 제공하고, 아티스트가 최종 원화·얼굴·의상·조형을 독자적으로 제작하도록 계약한다. 고유 IP와 사진 근접 품질을 함께 통제하기 쉬워서다. B1과 초도 1종이라는 범위를 고정하되 저렴한 견적을 품질 증거로 삼지 않는다.

1. **① 지금**: 스타일라이즈드 PBR 가설, c01 한 종, GASP+스타일 보정 시험, 18a의 콘솔/데이터 교체 및 V-11/V-12 절차 승인. 지출 없음.
2. **② V-12 이후**: 소유자 채점으로 최종 룩·비율 확정 → 상표/라이선스 미확인 해소 → 견적/계약·에셋 발주 또는 구매 승인. 돈이 드는 모든 실행은 이 뒤다.

V-12는 Fable PC 세션이 골목 Zone(없으면 `L_Basemap_Yeonnam`)에 18a 프록시+PBR/5.8 Toon BSDF/장난감 재질을 두고 조명 4개·포토 모드로 촬영한다. 스타일 최종 판정은 소유자, 엔진 품질 분석은 Fable 담당이다. 크기/카메라 프록시가 실제 4.5등신 모델을 대신할 수 없다는 한계를 채점표에 적는다.

## B6. 외주 의뢰서 초안

[캐릭터 제작 의뢰서](../outreach/character-commission-draft.md)에 B1 사양·원본/FBX/UE 납품·수정2회씩·4~7주 계획·저작재산권 양도 협의·비공개 보관/협업자 공유·AI 사전 고지 조항을 작성했다. 미발송이며 소유자가 ② 승인 후 조건을 채운다.
