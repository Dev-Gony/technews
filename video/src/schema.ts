import { z } from "zod";

// shorts.py가 만드는 props.json과 같은 구조. 타이밍은 모두 프레임 단위.

export const barSchema = z.object({
  label: z.string(),
  value: z.number(),
  display: z.string(),
});

export const roomSchema = z.object({
  place: z.string(),
  actual: z.string(),
  // 층 위에 올릴 사물 (Isometric.tsx의 ICONS 중 하나)
  icon: z.string().optional(),
});

// 구조도의 마디: 사물 아이콘 + 이름
export const nodeSchema = z.object({
  label: z.string(),
  icon: z.string().optional(),
});

// 전후 비교의 한쪽
export const sideSchema = z.object({
  title: z.string(),
  value: z.string(),
  icon: z.string().optional(),
});

// 3D 장면 배역 하나: 장면 속 대상(anchor 이름) + 화면에 붙일 이름표(12자 이내)
export const beatSchema = z.object({
  target: z.string(),
  label: z.string(),
});

// 3D 장면 이름 (Background.tsx SCENES_3D, shorts.py SCENE3D_FILES 와 같아야 한다)
export const SCENE3D_NAMES = [
  "desk3d", "vault3d", "coins3d", "server3d", "lab3d", "data3d", "web3d", "repo3d", "launch3d",
  "law3d", "chip3d", "phone3d", "deploy3d", "media3d", "search3d", "invest3d", "terminal3d",
  "chat3d", "voice3d", "robot3d", "ai3d", "lang3d", "work3d", "game3d", "math3d",
] as const;

export const visualSchema = z.object({
  // hook: 첫 컷 대형 문구 / metaphor: 공간·역할 비유 입체 건물 / number: 숫자 카운트업 / compare: 막대 비교 / flow: 단계 흐름도
  // keywords: 핵심 단어 카드 / code: 터미널 코드 / question: 질문 카드 / none: 자막만
  // diagram: 사물 구조도(흐르는 화살표 + 카메라 줌인) / beforeafter: 전후 비교 / scale: 아이콘 격자로 규모 / quote: 원문 인용 카드
  type: z.enum([
    "hook", "metaphor", "number", "compare", "flow", "keywords", "code", "question", "none",
    "diagram", "beforeafter", "scale", "quote", "scene3d",
  ]),
  value: z.string().optional(),
  label: z.string().optional(),
  items: z.array(z.string()).optional(),
  bars: z.array(barSchema).optional(),
  code: z.string().optional(),
  // code: 노란 띠로 강조할 줄 번호(1부터). explain/news 스타일의 코드 창에서 커서가 그 줄로 간다.
  highlight: z.number().int().optional(),
  rooms: z.array(roomSchema).optional(),
  nodes: z.array(nodeSchema).optional(),
  // 구조도에서 마지막에 카메라가 밀고 들어갈 마디 번호
  focus: z.number().int().optional(),
  before: sideSchema.optional(),
  after: sideSchema.optional(),
  // 규모: 아이콘 개수와 종류
  count: z.number().int().optional(),
  icon: z.string().optional(),
  quote: z.string().optional(),
  // scene3d: 미리 렌더링한 3D 장면 (Background.tsx SCENES_3D)
  scene: z.enum(SCENE3D_NAMES).optional(),
  // scene3d 배역: 장면 속 사물·꼬마(public/assets3d/*_anchors.json 의 이름)에 대사 속 개념을 붙여 차례로 보여 준다
  beats: z.array(beatSchema).optional(),
});

export const chunkSchema = z.object({
  text: z.string(),
  from: z.number().int().min(0),
  durationInFrames: z.number().int().positive(),
  emphasis: z.boolean(),
});

export const cutSchema = z.object({
  from: z.number().int().min(0),
  durationInFrames: z.number().int().positive(),
  visual: visualSchema,
  chunks: z.array(chunkSchema),
});

export const sfxSchema = z.object({
  src: z.string(),
  from: z.number().int().min(0),
  volume: z.number(),
});

export const shortSchema = z.object({
  channel: z.string(),
  // 배경 테마: ink(먹색) / paper(종이색)
  theme: z.enum(["ink", "paper", "news", "explain"]).optional(),
  // 화면 스타일: classic(기존 먹색·3D) / news(크림 잡지) / explain(남색 다크 + 코드 창). 없으면 classic.
  style: z.enum(["classic", "news", "explain"]).optional(),
  // 영상 내내 상단에 고정되는 제목. 어느 장면이 썸네일로 잡혀도 무슨 영상인지 보이게.
  cover: z.string(),
  source: z.string(),
  audio: z.string(),
  durationInFrames: z.number().int().positive(),
  cuts: z.array(cutSchema),
  // 마무리 장면이 시작되는 프레임 (마지막 대사 뒤). 없으면 마무리 없음.
  outroFrom: z.number().int().optional(),
  // 배경: glow(장면마다 옮겨 가는 빛) / type(빛 + 장면 핵심어 지면 타이포)
  // 3D 장면(빛 + 미리 렌더링한 Blender 루프, public/assets3d/*_loop.webm. Background.tsx SCENES_3D):
  // desk3d 책상 위 꼬마 에이전트들 / vault3d 금고(보안) / coins3d 저울·동전(비용) / server3d 서버실(인프라) / lab3d 점수판·시상대(연구)
  backdrop: z.enum(["glow", "type", ...SCENE3D_NAMES]).optional(),
  sfx: z.array(sfxSchema),
});

export type Visual = z.infer<typeof visualSchema>;
export type Chunk = z.infer<typeof chunkSchema>;
export type Cut = z.infer<typeof cutSchema>;
export type ShortProps = z.infer<typeof shortSchema>;
