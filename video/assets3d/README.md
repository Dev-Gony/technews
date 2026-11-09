# assets3d — Blender로 미리 만드는 3D 장면

서버에는 GPU가 없으므로 Blender는 **사용자 PC에서 한 번만** 돌린다.
결과물(투명 PNG, 투명 WebM 루프)을 `public/assets3d/`에 넣어 두고, 매일 쇼츠는 그 파일을 가져다 쓰기만 한다.
제목, 숫자 칩, 자막 같은 글자는 Remotion이 위에 그린다(3D는 배경 장면만 맡는다).

## 장면

| 스크립트 | 결과물 | 내용 |
| --- | --- | --- |
| `scripts/desk_world.py` | `public/assets3d/desk_world.png`, `desk_world_loop.webm` | 책상 위 꼬마 에이전트들. 노트북 앞을 꼬마 4명이 종종걸음으로 돌고(토큰, 코드, 문서를 나름), 1명은 키보드 위에서 통통, 1명은 화면 위에 걸터앉아 있다. 4초 끊김 없는 루프 |

`scripts/iso_kit.py`는 모든 장면이 같이 쓰는 틀이다. 카메라(9:16), 조명, 팔레트 재질, 둥근 도형, 출력(PNG, VP9 알파 WebM)을 담당한다.

## 다시 만들기

Blender 5.2 (`winget install --id BlenderFoundation.Blender -e`), `video` 폴더에서 실행한다.

```bash
blender -b -P assets3d/scripts/desk_world.py                  # 정지 + 4초 루프 (RTX 3050 Ti 기준 약 2분)
blender -b -P assets3d/scripts/desk_world.py -- --still-only  # 정지만 (약 10초)
```

WebM 인코딩에는 Remotion에 들어 있는 ffmpeg(`node_modules/@remotion/compositor-win32-x64-msvc/ffmpeg.exe`)을 쓴다. 없으면 `FFMPEG` 환경변수로 경로를 지정한다.

## 미리보기

```bash
npx remotion render src/lab/index.ts DeskShort out.mp4
```

`src/lab/`은 시안 확인용 별도 진입점이다. 매일 쓰는 `src/Root.tsx`(Short)와는 연결되어 있지 않다.
