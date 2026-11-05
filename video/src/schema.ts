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
});

export const visualSchema = z.object({
  // hook: 첫 컷 대형 문구 / metaphor: 공간·역할 비유 입체 건물 / number: 숫자 카운트업 / compare: 막대 비교 / flow: 단계 흐름도
  // keywords: 핵심 단어 카드 / code: 터미널 코드 / question: 질문 카드 / none: 자막만
  type: z.enum(["hook", "metaphor", "number", "compare", "flow", "keywords", "code", "question", "none"]),
  value: z.string().optional(),
  label: z.string().optional(),
  items: z.array(z.string()).optional(),
  bars: z.array(barSchema).optional(),
  code: z.string().optional(),
  rooms: z.array(roomSchema).optional(),
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
  sfx: z.array(sfxSchema),
});

export type Visual = z.infer<typeof visualSchema>;
export type Chunk = z.infer<typeof chunkSchema>;
export type Cut = z.infer<typeof cutSchema>;
export type ShortProps = z.infer<typeof shortSchema>;
