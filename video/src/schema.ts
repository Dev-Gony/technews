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

export const visualSchema = z.object({
  // hook: 첫 컷 대형 문구 / metaphor: 공간·역할 비유 입체 건물 / number: 숫자 카운트업 / compare: 막대 비교 / flow: 단계 흐름도
  // keywords: 핵심 단어 카드 / code: 터미널 코드 / question: 질문 카드 / none: 자막만
  // diagram: 사물 구조도(흐르는 화살표 + 카메라 줌인) / beforeafter: 전후 비교 / scale: 아이콘 격자로 규모 / quote: 원문 인용 카드
  type: z.enum([
    "hook", "metaphor", "number", "compare", "flow", "keywords", "code", "question", "none",
    "diagram", "beforeafter", "scale", "quote",
  ]),
  value: z.string().optional(),
  label: z.string().optional(),
  items: z.array(z.string()).optional(),
  bars: z.array(barSchema).optional(),
  code: z.string().optional(),
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
  theme: z.enum(["ink", "paper"]).optional(),
  // 영상 내내 상단에 고정되는 제목. 어느 장면이 썸네일로 잡혀도 무슨 영상인지 보이게.
  cover: z.string(),
  source: z.string(),
  audio: z.string(),
  durationInFrames: z.number().int().positive(),
  cuts: z.array(cutSchema),
  // 마무리 장면이 시작되는 프레임 (마지막 대사 뒤). 없으면 마무리 없음.
  outroFrom: z.number().int().optional(),
  // 배경: glow(장면마다 옮겨 가는 빛) / type(빛 + 장면 핵심어 지면 타이포)
  backdrop: z.enum(["glow", "type"]).optional(),
  sfx: z.array(sfxSchema),
});

export type Visual = z.infer<typeof visualSchema>;
export type Chunk = z.infer<typeof chunkSchema>;
export type Cut = z.infer<typeof cutSchema>;
export type ShortProps = z.infer<typeof shortSchema>;
