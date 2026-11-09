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

결과물은 모두 `public/assets3d/`에 있고, 1080x1920 투명 배경이다. 루프는 **12초(360프레임)** 이다.
걷는 꼬마들은 루프 동안 정확히 한 바퀴를 돌아 제자리로 오므로 이음새가 보이지 않는다.
(1/n 바퀴만 돌게 하면 이음새에서 색이 다른 꼬마가 옆자리로 순간 이동해 튄다.) 깜빡임, 통통, 흔들림은 4초에 정수 번 반복한다.

어떤 장면을 고를지는 `shorts.py`의 `SCENE3D_KEYWORDS`가 정한다. 제목 주제어는 3점, 대사 주제어는 1점으로 세고,
제목에 1개 이상 또는 대사에 2개 이상 나온 장면 중 점수가 가장 높은 장면을 고른다(같으면 보안 > 비용 > 인프라 > 연구 > 책상).
맞는 장면이 없거나 루프 파일이 없으면 기본 배경(glow)을 쓴다.

`scripts/iso_kit.py`는 모든 장면이 같이 쓰는 틀이다. 카메라(9:16), 조명, 팔레트 재질, 둥근 도형, 출력(PNG, VP9 알파 WebM)을 담당한다.
`scripts/chibi_kit.py`는 그 위의 두 번째 틀이다. 꼬마 캐릭터, 받침 원판, 걷기·통통 애니메이션, 책상 장면과 똑같은 카메라를 담당한다.

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
