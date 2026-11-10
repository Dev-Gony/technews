# assets3d — Blender로 미리 만드는 3D 장면

서버에는 GPU가 없으므로 Blender는 **사용자 PC에서 한 번만** 돌린다.
결과물(투명 PNG, 투명 WebM 루프)을 `public/assets3d/`에 넣어 두고, 매일 쇼츠는 그 파일을 가져다 쓰기만 한다.
제목, 숫자 칩, 자막 같은 글자는 Remotion이 위에 그린다(3D는 배경 장면만 맡는다).

## 장면

| 스크립트 | 배경 이름 | 결과물 | 내용 | 고르는 주제 |
| --- | --- | --- | --- | --- |
| `scripts/desk_world.py` | `desk3d` | `desk_world.png`, `desk_world_loop.webm` | 노트북 앞을 꼬마 4명이 종종걸음으로 돌고(토큰, 코드, 문서를 나름), 1명은 키보드 위에서 통통, 1명은 화면 위에 걸터앉아 있다 | 에이전트, 토큰, 코딩 도구 |
| `scripts/vault_world.py` | `vault3d` | `vault_world.png`, `vault_world_loop.webm` | 살짝 열린 금고 문틈으로 빨간 빛이 새고, 빨간 방패와 금색 자물쇠, 꼬마가 문틈을 엿본다 | 백도어, 유출, 인증, DMARC, 취약점 |
| `scripts/coins_world.py` | `coins3d` | `coins_world.png`, `coins_world_loop.webm` | 동전 쪽으로 기운 저울, 낮아지는 동전 탑과 빨간 화살표, 바닥에 길게 깔린 영수증 | 비용, 사용료, 가격 인하, % 절감 |
| `scripts/server_world.py` | `server3d` | `server_world.png`, `server_world_loop.webm` | 서버 랙 3대의 LED, 케이블을 따라 허브로 흐르는 빛 알갱이, 구름, 메모리 막대, 속도계 | 서버, 클라우드, EC2, RAM, 성능 n배 |
| `scripts/lab_world.py` | `lab3d` | `lab_world.png`, `lab_world_loop.webm` | 막대가 오르내리는 점수판, 1·2·3등 시상대(트로피 꼬마), 기포가 오르는 실험대, 논문 더미 | 가중치, 학습, 벤치마크, 안전 연구 |
| `scripts/data_world.py` | `data3d` | `data_world.png`, `data_world_loop.webm` | 3단 DB 원통(단 사이 금색 빛 띠), 표에서 한 행씩 골라지는 쿼리, 빠졌다 들어가는 원그래프 조각, 관을 따라 흐르는 빛 알갱이 | 데이터, DB, SQL, 지표, 대시보드 |
| `scripts/web_world.py` | `web3d` | `web_world.png`, `web_world_loop.webm` | 떠 있는 브라우저 창(점 3개, 주소창, 로딩 막대, 톡 튀는 카드), 도는 지구본, 빨간 버튼을 누르는 화살표 | 웹, 브라우저, 사이트, 프런트엔드 |
| `scripts/repo_world.py` | `repo3d` | `repo_world.png`, `repo_world_loop.webm` | 갈라졌다 합쳐지는 깃 가지 그래프와 깃발, 열린 패키지 상자에서 튀는 코드 블록, 도는 금색 별 | 오픈소스, 깃허브, Git, 라이브러리, PR |
| `scripts/launch_world.py` | `launch3d` | `launch_world.png`, `launch_world_loop.webm` | 발사대 위 로켓(불꽃, 연기), 발사탑, 3·2·1 카운트다운, 뚜껑이 들썩이는 선물 상자 | 새 모델·제품 출시, 공개, 베타 |
| `scripts/law_world.py` | `law3d` | `law_world.png`, `law_world_loop.webm` | 기둥 4개 법원 건물, 땅땅 내려치는 의사봉과 금색 물결, 서류에 쾅 찍히는 빨간 도장 | 법, 규제, 소송, 저작권, 약관 |
| `scripts/chip_world.py` | `chip3d` | `chip_world.png`, `chip_world_loop.webm` | 금색 다리가 난 큰 칩(빛나는 다이), 칩으로 흘러드는 회로 선, 도는 웨이퍼, 냉각 팬 | 칩, 반도체, GPU, NPU, 하드웨어 |
| `scripts/phone_world.py` | `phone3d` | `phone_world.png`, `phone_world_loop.webm` | 앱 아이콘이 차례로 튀는 큰 스마트폰과 알림 말풍선, 태블릿, 흔들리는 알림 종 | 모바일, 앱, iOS, Android |
| `scripts/deploy_world.py` | `deploy3d` | `deploy_world.png`, `deploy_world_loop.webm` | 빌드 톱니 → 검사 터널 → 체크 깃발로 상자가 흐르는 컨베이어, 신호등 | 배포, CI/CD, 테스트, 빌드, 모니터링 |
| `scripts/media_world.py` | `media3d` | `media_world.png`, `media_world_loop.webm` | 이젤 위 산·해 그림(붓이 오감), 떠 있는 사진 3장, 딱 닫히는 슬레이트, 릴이 도는 캠코더 | 이미지·영상 생성, 사진, 디자인 |
| `scripts/search_world.py` | `search3d` | `search_world.png`, `search_world_loop.webm` | 입력이 쳐지는 큰 검색창, 결과 카드를 훑는 돋보기(밑 카드가 골라짐), 책 더미 | 검색, RAG, 추천, 임베딩 |
| `scripts/invest_world.py` | `invest3d` | `invest_world.png`, `invest_world_loop.webm` | 창문이 켜지는 빌딩 3채, 치솟는 빨간 화살표, 통통 튀는 돈 자루, 지폐 다발 | 투자, 스타트업, 상장, 인수 |
| `scripts/terminal_world.py` | `terminal3d` | `terminal_world.png`, `terminal_world_loop.webm` | 한 줄씩 쳐지는 터미널 창과 깜빡이는 커서, 맞물려 도는 톱니바퀴, 폴더 | 터미널, CLI, 리눅스, macOS, OS |
| `scripts/chat_world.py` | `chat3d` | `chat_world.png`, `chat_world_loop.webm` | 뚜껑이 열리고 편지가 올라오는 봉투, 말풍선(입력 중 점 3개), 원판을 도는 종이비행기 | 메일, 메신저, 채팅, 슬랙 |
| `scripts/voice_world.py` | `voice3d` | `voice_world.png`, `voice_world_loop.webm` | 스튜디오 마이크와 퍼지는 음파 고리, 오르내리는 음파 막대, 헤드폰, 음표 | 음성, TTS, STT, 오디오, 음악 |
| `scripts/robot_world.py` | `robot3d` | `robot_world.png`, `robot_world_loop.webm` | 손 흔드는 네모 로봇, 둥근 길을 도는 라이다 자율주행차, 드론, 고깔 | 로봇, 휴머노이드, 자율주행, 드론 |
| `scripts/ai_world.py` | `ai3d` | `ai_world.png`, `ai_world_loop.webm` | 빛이 흐르는 3겹 신경망, 도는 금색 반짝이, 'AI' 말풍선 | AI 모델·LLM·챗봇 일반 (다른 장면이 안 맞을 때만) |

결과물은 모두 `public/assets3d/`에 있고, 1080x1920 투명 배경이다. 루프는 **12초(360프레임)** 이다.
걷는 꼬마들은 루프 동안 정확히 한 바퀴를 돌아 제자리로 오므로 이음새가 보이지 않는다.
(1/n 바퀴만 돌게 하면 이음새에서 색이 다른 꼬마가 옆자리로 순간 이동해 튄다.) 깜빡임, 통통, 흔들림은 4초에 정수 번 반복한다.

어떤 장면을 고를지는 `shorts.py`의 `SCENE3D_KEYWORDS`가 정한다. 제목 주제어는 3점, 대사 주제어는 1점으로 세고,
제목에 1개 이상 또는 대사에 2개 이상 나온 장면 중 점수가 가장 높은 장면을 고른다(같으면 `SCENE3D_FILES` 순서: 보안 > 법 > 비용 > 인프라 > 칩 > 연구 > 데이터 > 영상 > 검색 > 투자 > 웹 > 배포 > 터미널 > 오픈소스 > 책상 > 모바일 > 출시, 로봇은 칩 뒤·음성은 영상 뒤·메일은 웹 뒤).
`ai3d`(AI 일반)는 `SCENE3D_FALLBACK`이라 다른 장면이 하나도 맞지 않을 때만 고른다.
'앱', 출시·공개처럼 넓은 말을 쓰는 장면은 뒤에 두어, 더 구체적인 주제와 겹치면 구체적인 장면이 이긴다.
맞는 장면이 없거나 루프 파일이 없으면 기본 배경(glow)을 쓴다.

`scripts/iso_kit.py`는 모든 장면이 같이 쓰는 틀이다. 카메라(9:16), 조명, 팔레트 재질, 둥근 도형, 출력(PNG, VP9 알파 WebM)을 담당한다.
`scripts/chibi_kit.py`는 그 위의 두 번째 틀이다. 꼬마 캐릭터, 받침 원판, 걷기·통통 애니메이션, 책상 장면과 똑같은 카메라를 담당한다.
장면 이름 목록은 `video/src/schema.ts`의 `SCENE3D_NAMES`, `Background.tsx`의 `SCENES_3D`, `shorts.py`의 `SCENE3D_FILES` 세 곳이 같아야 한다(타입 검사와 테스트가 확인한다).
관(`tube`)과 그 위를 흐르는 점(`sample`), 원뿔(`cone`), 원그래프 조각(`wedge`), 보였다 숨기기(`show`)도 여기 있다.

## 다시 만들기

Blender 5.2 (`winget install --id BlenderFoundation.Blender -e`), `video` 폴더에서 실행한다.

```bash
blender -b -P assets3d/scripts/desk_world.py                  # 정지 + 12초 루프 (RTX 3050 Ti 기준 약 6분)
blender -b -P assets3d/scripts/desk_world.py -- --still-only  # 정지만 (약 10초)
```

WebM 인코딩에는 Remotion에 들어 있는 ffmpeg(`node_modules/@remotion/compositor-win32-x64-msvc/ffmpeg.exe`)을 쓴다. 없으면 `FFMPEG` 환경변수로 경로를 지정한다.

## 미리보기

```bash
npx remotion render src/lab/index.ts DeskShort out.mp4
```

`src/lab/`은 시안 확인용 별도 진입점이다. 매일 쓰는 `src/Root.tsx`(Short)와는 연결되어 있지 않다.
