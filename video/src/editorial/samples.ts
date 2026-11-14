import type { ShortProps } from "../schema";

// Studio·스틸 확인용 샘플 (2026-11-14 GONY DAILY 기사 요약에 있는 내용만 사용)
const chunk = (text: string, from: number, durationInFrames: number, emphasis = false) => ({ text, from, durationInFrames, emphasis });

export const SAMPLE_NEWS: ShortProps = {
  channel: "itgony",
  style: "news",
  cover: "재학습 없이\n성공률 22%→85%",
  source: "출처: GeekNews · news.hada.io",
  audio: "sample/silence.mp3",
  durationInFrames: 330,
  outroFrom: 270,
  sfx: [],
  cuts: [
    { from: 0, durationInFrames: 50, visual: { type: "hook" }, chunks: [chunk("실험만", 0, 22), chunk("600번.", 22, 28, true)] },
    {
      from: 50,
      durationInFrames: 80,
      visual: {
        type: "beforeafter",
        label: "작업 성공률",
        before: { title: "기존", value: "22%", icon: "robot" },
        after: { title: "계획 변경", value: "85%", icon: "robot" },
      },
      chunks: [chunk("성공률이", 0, 30), chunk("22%에서 85%로", 30, 50, true)],
    },
    {
      from: 130,
      durationInFrames: 70,
      visual: { type: "flow", items: ["긴 과제", "25스텝 분할", "메모리 그래프", "경로 탐색"] },
      chunks: [chunk("25스텝씩", 0, 35, true), chunk("잘라서 계획해요", 35, 35)],
    },
    {
      from: 200,
      durationInFrames: 70,
      visual: { type: "keywords", items: ["정밀도 < 계획", "재학습 0번"] },
      chunks: [chunk("정밀도보다", 0, 35), chunk("계획이 컸죠", 35, 35, true)],
    },
  ],
};

export const SAMPLE_EXPLAIN: ShortProps = {
  channel: "itgony",
  style: "explain",
  cover: "C 대신 Zig?\nGC 없이 안전",
  source: "출처: GeekNews · news.hada.io",
  audio: "sample/silence.mp3",
  durationInFrames: 330,
  outroFrom: 270,
  sfx: [],
  cuts: [
    { from: 0, durationInFrames: 50, visual: { type: "hook" }, chunks: [chunk("GC는 없는데", 0, 25), chunk("안전하다?", 25, 25, true)] },
    {
      from: 50,
      durationInFrames: 110,
      visual: {
        type: "code",
        label: "main.zig",
        highlight: 3,
        code: "fn load(alloc: Allocator) !Buf {\n    const buf = try alloc.alloc(u8, 4096);\n    errdefer alloc.free(buf);\n    try readInto(buf);\n    return .{ .data = buf };\n}",
      },
      chunks: [chunk("errdefer로", 0, 50, true), chunk("오류 날 때만 정리", 50, 60)],
    },
    {
      from: 160,
      durationInFrames: 110,
      visual: { type: "code", label: "zsh", code: "$ zig build run\n# 슬라이스 범위 검사\n# comptime: 컴파일 때 실행" },
      chunks: [chunk("범위 밖 접근은", 0, 55), chunk("언어가 막아요", 55, 55, true)],
    },
  ],
};
