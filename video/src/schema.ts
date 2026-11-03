import { z } from "zod";

// shorts.py가 만드는 props.json과 같은 구조

export const wordSchema = z.object({
  text: z.string(),
  startMs: z.number(),
  endMs: z.number(),
});

export const barSchema = z.object({
  label: z.string(),
  value: z.number(),
  display: z.string(),
});

export const visualSchema = z.object({
  // number: 큰 숫자 카운트업 / compare: 막대 비교 / flow: 단계 흐름도
  // keywords: 핵심 단어 카드 / code: 터미널 코드 / question: 질문 카드 / none: 헤드라인만
  type: z.enum(["number", "compare", "flow", "keywords", "code", "question", "none"]),
  value: z.string().optional(),
  label: z.string().optional(),
  items: z.array(z.string()).optional(),
  bars: z.array(barSchema).optional(),
  code: z.string().optional(),
});

export const sceneSchema = z.object({
  headline: z.string(),
  narration: z.string(),
  audio: z.string(),
  durationInFrames: z.number().int().positive(),
  words: z.array(wordSchema),
  visual: visualSchema,
});

export const shortSchema = z.object({
  channel: z.string(),
  source: z.string(),
  scenes: z.array(sceneSchema),
});

export type Word = z.infer<typeof wordSchema>;
export type Visual = z.infer<typeof visualSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type ShortProps = z.infer<typeof shortSchema>;

export const TRANSITION_FRAMES = 10;
