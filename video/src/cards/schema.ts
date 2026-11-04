import { z } from "zod";

// cards.py가 만드는 props.json과 같은 구조. 프레임 하나가 카드 한 장이다.

export const slideSchema = z.object({
  // cover: 표지 / story: 무슨 일 / number: 핵심 숫자 / flow: 원리·과정
  // checklist: 바로 써먹는 법 / caution: 주의 / outro: 마지막 장(질문·저장 유도)
  type: z.enum(["cover", "story", "number", "flow", "checklist", "caution", "outro"]),
  label: z.string().optional(),
  title: z.string().optional(),
  body: z.string().optional(),
  value: z.string().optional(),
  items: z.array(z.string()).optional(),
});

export const cardsSchema = z.object({
  masthead: z.string(),
  date: z.string(),
  section: z.string(),
  handle: z.string(),
  source: z.string(),
  slides: z.array(slideSchema),
});

export type Slide = z.infer<typeof slideSchema>;
export type CardsProps = z.infer<typeof cardsSchema>;
