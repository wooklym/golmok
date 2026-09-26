# WP-18 — 컨셉 이미지 생성 프롬프트

2026-09-26 · 도구: OpenAI 내장 `image_gen` (CLI/API 별도 실행 없음).
도구 응답에서 모델 버전을 제공하지 않아 특정 모델명은 적지 않는다.
최종 JPG 7장은 [컨셉 A4](character-concept.md#a4-컨셉-이미지)에서 확인한다.

모든 신규 이미지는 아래 자체 텍스트만 입력했다. P01-edit만 이번에 생성한 P01 그림을 편집 대상으로 사용했다. 실제 촬영물·실존 인물·상점·Fab 자산과 스크린샷·기존 IP 그림을 입력하지 않았다. 파일 변환은 Pillow로 RGB JPG 저장/긴 변1600px 이하만 적용했다. 그림 수정·문구 추가는 image_gen 안에서 처리했다. 프롬프트의 cm·등신·색은 목표이며 출력의 정확한 치수나 엔진 조명을 보증하지 않는다.

## p01

첫 생성. 제출 턴어라운드는 아래 편집본이다.

```text
Use case: stylized-concept. Create one landscape character turnaround sheet for an original game character, code c01, working name Morubit (모루빛). This is concept reference for Golmok, a Seoul alley exploration game. A clearly adult woman in her twenties, friendly curious neighborhood color sketcher, 135cm design stature, exactly 4.5 heads tall, enlarged but tastefully adult head, asymmetrical dark ink short bob, softly angular face, a small asymmetric side part, NOT a child. Peach #E9A481 hip-length cropped jacket with curved side seam, dark ink #293E56 loose wide trousers, cream #F3E7CF simple unbranded flat sneakers, mint #84B8A8 tiny cuff accent. Unbranded small square crossbody satchel at hip, plain sketchbook. Original distinctive readable silhouette, humanoid biped, two arms two legs, modest everyday clothing. Stylized PBR 3D art direction, opaque cloth with broad roughness detail, natural ambient and soft contact shadows, gentle real material response, no plastic toy gloss, no toon outline. On warm neutral studio background, show THREE full-body views of precisely the SAME character in aligned front, side and back poses, same proportions and wardrobe, feet on same baseline, clear space between views, shoulders and arms relaxed in mild A-pose. No extra characters or environments. High quality production concept sheet with detailed modeling and coherent garment structure. Small header 'c01 / Morubit'; compact color swatches at bottom optional. All signage, logos, real people, landmarks, brand marks, existing mascots forbidden. Bottom footer must display EXACT Korean text clearly: '컨셉 참고용, 최종 에셋 아님'. This must be legible and accurate. Wide aspect ratio around 3:2.
```

## p01-edit

P01 자체 출력만 편집 입력으로 사용. 최종 제출본.

```text
Edit this original Morubit character turnaround sheet. Preserve her face identity, adult age, asymmetric short dark bob, peach jacket, mint cuffs, ink wide trousers, cream shoes, square satchel, materials and palette. Correct the proportions in ALL three aligned full-body views: make her head about 20% larger relative to the body and compress torso and legs so full standing height is about 4.5 head lengths instead of the present roughly 5.2. Keep clearly adult stylized anatomy and adult face, two arms and two legs. Shorter but proportionate limbs, hands remain adult. Make the front, side, and back correspond precisely in height, garment length and head size. Keep the same landscape sheet composition and detailed closeups. Keep the bottom Korean footer EXACTLY '컨셉 참고용, 최종 에셋 아님', legible. No brand marks or new props. This is an art-reference proportion correction, not a real-person photo.
```

## p02-initial

텍스트 신규 생성, 미선택. 연령감/직사광 수정 대상으로 제외.

```text
Use case: stylized-concept. Generate one beautiful landscape mood image using ONLY this text, no input images. Original character c01 Morubit (모루빛), clearly adult woman in twenties, friendly curious neighborhood color sketcher, petite stylized 135cm and 4.5-head-tall proportions with short adult limbs and enlarged head; asymmetrical short dark ink bob with side part, softly angular kind face, peach #E9A481 jacket, rolled mint #84B8A8 cuffs, ink #293E56 wide trousers, cream #F3E7CF unbranded flat sneakers, plain square crossbody satchel and blank sketchbook. Cute stylized PBR game character with credible opaque cloth and skin roughness, no outline, not a real person. She pauses in a quiet FICTIONAL Seoul residential alley to notice light on a plain green metal gate, holding sketchbook at waist and smiling slightly. Full body readable, three-quarter view, shoes firmly contact pavement. Realistically textured gray concrete, muted red brick wall, pots of unbranded greenery, small stair and drain, ordinary modest walls, NO recognizable actual building or landmark. Soft cloudy daylight with gentle warm reflected light, contact shadow under shoes and plausible shadow on wall, natural GI color, editorial game art composition with foreground detail and restrained depth of field. Calm lived-in environment without clutter drowning silhouette. No other people, no cars with plates, absolutely NO storefronts, NO signs, NO writing on buildings, NO brand names or logos or symbols. Character is a stylized illustration, not a likeness of any real person or existing character. Add only a small unobtrusive yet clearly readable bottom footer strip with EXACT Korean text '컨셉 참고용, 최종 에셋 아님'. 3:2 landscape.
```

## p02-adult-trial

텍스트 신규 생성, 미선택. 길어진 현실적 신체 비율로 제외.

```text
Use case: stylized-concept. Generate ONE landscape mood illustration from ONLY THIS TEXT, without any image inputs. Original game character c01 / Morubit (모루빛), a clearly adult Korean woman aged 26, a small stylized neighborhood sketcher. Adult softly angular face with a defined jaw and chin, medium almond-shaped brown eyes (not giant round eyes), subtle eyelids, a natural proportioned nose and thin adult brows; warm restrained smile, no infant cheeks or child appearance. Asymmetric chin-length dark bob with off-center side part, one side tucked back. Petite 135cm design stature, compact stylized 4.5-head proportions, but visibly adult anatomy and adult face. Cropped peach #E9A481 plain jacket with rolled mint #84B8A8 cuffs, cream shirt, ink navy #293E56 very wide full-length trousers, cream #F3E7CF flat unbranded sneakers. Plain small square dark crossbody satchel, blank sketchbook held at waist. Stylized PBR 3D game art: realistic opaque cloth weave, softly stylized face, gentle broad roughness, no plastic toy shine, no cartoon outlines. Full body three-quarter standing pose with shoes firmly on pavement, pausing to consider the color of a plain green gate. FICTIONAL Seoul quiet residential alley: weathered gray concrete, muted red brick, plain green metal gate, small unbranded plant pots, a drain and low stair, ordinary walls. Low-contrast OVERCAST diffuse daylight, no sharp sunbeam, gentle foot contact shadow and soft wall shadow. Natural game camera composition with enough alley visible to compare scale, restrained depth of field. No other people, absolutely no signs, storefront lettering, addresses, real brands, logos, landmarks, actual identifiable buildings or photographed assets. This is a completely invented illustrated person and place, not any real person. Do NOT use a childish animation-film facial style. Only text is the clearly readable exact bottom Korean footer '컨셉 참고용, 최종 에셋 아님'. 3:2 landscape.
```

## p02-final

텍스트 신규 생성, 최종 무드 제출본. 얼굴 연령감·정확한 등신은 최종 인간 원화 검수 항목.

```text
Use case: stylized-concept. TEXT-ONLY new image. Landscape game concept art of Morubit, an original cute stylized 3D ADULT woman miniature exploring a FICTIONAL Seoul residential alley. Crucial proportions: the standing figure is 4.5 heads tall, with a visibly enlarged head and SHORT legs and short torso. Her head occupies about 22% of the entire figure height. She is NOT a tall slender realistic woman. She is NOT an infant: use a young-adult softly angular face, gentle almond eyes, defined small chin and adult hands. A cozy stylized PBR videogame miniature with cloth texture and soft 3D skin shading. Design: asymmetric dark chin-length bob, peach #E9A481 cropped jacket, mint #84B8A8 rolled cuffs, cream shirt, very wide navy #293E56 SHORTENED trousers, flat cream #F3E7CF plain sneakers. Small square unbranded dark crossbody satchel and blank sketchbook held at waist. Her body silhouette is compact and wide, the ankles and knees proportionately short, head large. Design stature 135cm. Composition: full body occupies roughly 750 pixels vertically in a 1536x1024 landscape image, and the head alone about 165 pixels high; feet visible touching pavement. She stands at left center facing a simple green metal gate, calmly enjoying the color, three-quarter view. Realistically textured yet fictional narrow alley, muted red brick and gray concrete, low steps and modest potted greenery. Soft overcast diffuse lighting, subtle contact shadow under feet, soft shadow on wall, depth of field restrained, quiet friendly mood. This is fully synthetic illustration, no real location or person reference. Absolutely no people besides her, no actual signs, no addresses, no letters on buildings, no brands, no logos, no recognizable landmarks, no vehicles. Do not make her a photorealistic tall adult or a baby. The ONLY text is exact clear bottom footer: '컨셉 참고용, 최종 에셋 아님'.
```

## p03

최종 c02.

```text
Use case: stylized-concept. Create one landscape original game character concept sheet, c02 / Duon (두온), for a quiet Seoul alley exploration game. A Korean man in his sixties, warm quietly humorous plant hobbyist, silver short hair with a subtle off-center wave, gentle age lines, distinctive broad shoulders and round belly, adult masculine face, about 145cm stylized five-head-tall proportions. Ochre #CBA866 plain chunky knit cardigan, muted plum #55475C straight trousers, cream #EEE6D5 flat unbranded walking shoes, a soft unbranded cloth tote containing a tiny potted plant. Readable square-round silhouette, human biped with two arms and two legs. Pose: full-body three-quarter view, leaning a little to inspect a leaf held carefully at chest height, genuine adult hand anatomy. Smaller side thumbnail and face detail on the right, matching exact same design. Warm neutral pale studio background, subtle soft ground contact shadow, muted color swatches, tasteful small header 'c02 / Duon'. High quality stylized PBR 3D concept with tactile opaque knit and matte fabric, slight skin warmth, adult proportions, no plastic toy shine, no thick outlines. This is an ORIGINAL character, no resemblance to existing mascots, celebrities or real people; no logos, brands, text on clothing or tote, public symbols or landmarks. The ONLY other text must be a clearly readable bottom footer EXACTLY '컨셉 참고용, 최종 에셋 아님'. No actual photos or external assets used. 3:2 landscape.
```

## p04

최종 c03.

```text
Use case: stylized-concept. Create one polished landscape original game character concept sheet, c03 / Saegyeol (새결). Quiet curious Korean boy aged 11, 115cm design height and compact 4.5-head-tall stylized proportions, short springy dark curls, attentive eyes and small softly squared face. This is an invented illustrated child, no real child likeness or photographic reference. Modest practical everyday outfit: sky-blue #86B6D4 boxy unbranded utility vest over cream short-sleeved tee, mustard #D8BB65 small plain backpack, dark navy #354354 comfortable knee-length shorts, plain socks and rounded flat canvas sneakers. Distinct square vest/backpack silhouette, two normal arms with small hands, two legs. Main full-body three-quarter pose, looking thoughtfully at geometric paving patterns on a tiny abstract floor patch, one hand open to point out a pattern. Side and back small matching full-body sketches plus small happy-discovery expression detail on right. The main background is warm neutral studio paper, no actual location. Stylized PBR 3D rendering, tactile cloth, soft skin, clearly illustrated head proportion, gentle contact shadows, restrained palette, no plastic gloss or thick outlines. Small header 'c03 / Saegyeol' only. Original character, no existing IP, real brands, logos, school uniforms, school marks, real people, actual storefronts or landmarks. No decorative narrative text. Bottom footer MUST be exact readable Korean: '컨셉 참고용, 최종 에셋 아님'. Make a professional game preproduction reference, all figures fully clothed, no other people. 3:2 landscape.
```

## p05

최종 c04.

```text
Use case: stylized-concept. Create one landscape original game character concept sheet c04 / Narit (나릿), an invented nonbinary Korean adult in their thirties who enjoys framing light and shadow while walking through quiet neighborhoods. Fuller broad body, rounded shoulders, strong comfortable thighs, calm humorous adult face, short clipped sides and a soft wavy dark top haircut, 140cm design height, 4.5-head stylized compact adult proportions. Clothing: rounded plum #805970 zip jacket, oat #D9C9AB wide knee-length shorts, teal #397E82 plain unbranded flat walking shoes with cream socks, simple shirt. Small folded plain paper viewfinder held at upper chest, no electronics or logos. Human biped with two arms and two legs, gender-neutral clothing. Main full-body three-quarter pose, one foot slightly ahead with stable wide stance, looking through the paper frame without hiding face. Smaller full-body side/back views and face smile detail, identical consistent wardrobe and proportions. Warm neutral studio background, soft natural light and subtle floor contact shadows, quiet palette swatches. High quality stylized PBR 3D material concept with matte fabric weave, believable adult skin, simple readable silhouette, NO toy gloss or heavy outlines. Small title 'c04 / Narit' only, no extra narrative text. No existing characters, brands, logos, public symbols, landmarks, storefronts or real people. Bottom footer exact clearly legible Korean '컨셉 참고용, 최종 에셋 아님'. Landscape 3:2.
```

## p06

최종 c05.

```text
Use case: stylized-concept. Create one polished landscape original creature concept sheet c05 / Solmung (솔뭉), a small 85cm NON-HUMANOID pinecone spirit imagined for a quiet Seoul neighborhood exploration game. DISTINCTIVE ANATOMY: elongated asymmetrical tapering pinecone body leaning slightly to one side, exactly THREE big overlapping layers of rounded woody scales, two short twig arms, exactly THREE clearly visible small root-like FEET supporting a triangular stance, not a two-legged animal. Show all three feet clearly separated on the floor in the main front three-quarter view; side/back thumbnails must reflect this same three-foot anatomy. Small curious face set off-center within one scale, modest small eyes and tiny irregular mouth, not a big round plush animal face. Copper #AC704A warm woody scales, moss #758369 small accents in seams, ivory #E5D8BE light inner scale edges. No clothes, no accessories, no props, no animal ears or tail, no hats. This is a botanical fantasy creature with carved organic opaque surfaces and subtle bark texture, not a known mascot. Main full-body three-quarter view looking curiously down, smaller matching side and back full-body views plus scale/face closeups and palette swatches. Warm neutral studio background, grounded soft shadows, stylized PBR 3D concept quality, not plastic, no outlines. Original silhouette, no references to existing IP, public mascots, logos, real people or actual places. Small title 'c05 / Solmung'. Bottom footer EXACT readable Korean '컨셉 참고용, 최종 에셋 아님'. No other text. 3:2 landscape.
```

## p07

최종 c06.

```text
Use case: stylized-concept. Create one polished landscape original game character concept sheet c06 / Damul (담울), an anthropomorphic bird who quietly listens to the breeze in a fictional Seoul alley game. 125cm design height, 4-head-tall compact proportions. A narrow tapered head with a SMALL delicate short beak and modest observant eyes, squared broad torso, short squared tail, a long scarf-like sculpted feather ruff integrated into the neck. Exactly TWO human-proportioned articulated arms with stylized hands and exactly TWO human-like legs with stable grounded feet; HUMANOID BIPED skeleton intended for a mannequin retarget, NOT wings in place of arms, no flight. Gray-blue #718EA8 dense smooth feather masses, muted orange #DDA477 neck ruff and small ankle accents, dark charcoal #3E4650 torso/feet. Plain small unbranded cloth pouch at hip. Character should feel thoughtful, tactile and original, avoid giant cartoon beak or circular mascot body. Main full-body three-quarter standing pose with one hand gently tidying the neck feathers, smaller matching side/back views clearly show short tail and humanoid arms/legs, tiny face and hand detail. Warm neutral studio background, gentle physical light and contact shadow. Stylized PBR 3D game art with opaque layered feather shapes, broad roughness detail, no shiny toy plastic, no thick outline. No existing bird characters, brand names, public symbols, logos, real people or recognizable places. Small header 'c06 / Damul' only. Bottom footer EXACTLY '컨셉 참고용, 최종 에셋 아님' in clean readable Korean. No other text. 3:2 landscape.
```

