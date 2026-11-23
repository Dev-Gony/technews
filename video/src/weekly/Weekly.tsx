import { z } from "zod";
import { AbsoluteFill } from "remotion";
import { fontFamily, serifFamily } from "../theme";

// 주간 모음 영상(16:9)의 바탕 그림. 왼쪽 자리에 그 주의 쇼츠(9:16)를 ffmpeg로 얹고,
// 오른쪽에 이번 주 순위 목록을 보여 준다 (지금 나오는 순위는 검은 띠). weekly.py가 순위마다 한 장씩 만든다.
// mode "thumb"는 같은 디자인의 썸네일(1280x720).

const INK = "#15130F";
const PAPER = "#F4EFE3";
const CARD = "#FFFDF7";
const RED = "#C8402F";
const MUTED = "#6E675B";

export const weeklySchema = z.object({
  mode: z.enum(["panel", "thumb"]),
  heading: z.string(),
  range: z.string(),
  items: z.array(z.object({ rank: z.number().int(), title: z.string(), series: z.string().optional() })),
  current: z.number().int().nullable(),
  // 왼쪽 영상 자리 (panel). ffmpeg가 같은 자리에 쇼츠를 얹는다.
  slot: z.object({ x: z.number(), y: z.number(), width: z.number(), height: z.number() }).optional(),
  // 썸네일 큰 글씨 (thumb)
  cover: z.string().optional(),
});

export type WeeklyProps = z.infer<typeof weeklySchema>;

const Backdrop: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: PAPER }}>
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 80% 60% at 70% 0%, rgba(255,255,255,0.8), transparent 70%)" }} />
    <AbsoluteFill
      style={{
        backgroundImage: "repeating-linear-gradient(90deg, rgba(21,19,15,0.018) 0px, rgba(21,19,15,0.018) 1px, transparent 1px, transparent 6px)",
      }}
    />
  </AbsoluteFill>
);

const Row: React.FC<{ rank: number; title: string; series?: string; hot: boolean; size: number }> = ({ rank, title, series, hot, size }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: size * 0.7,
      padding: `${size * 0.32}px ${size * 0.6}px`,
      borderRadius: size * 0.4,
      background: hot ? INK : "transparent",
      color: hot ? PAPER : INK,
    }}
  >
    <div style={{ fontFamily: serifFamily, fontWeight: 900, fontSize: size * 1.5, width: size * 1.5, color: hot ? "#FF6A52" : RED, lineHeight: 1 }}>
      {rank}
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: size * 0.15, minWidth: 0 }}>
      {series ? (
        <div style={{ fontFamily, fontWeight: 800, fontSize: size * 0.55, color: hot ? "#C9C1B0" : MUTED, letterSpacing: 1 }}>{series}</div>
      ) : null}
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: size,
          lineHeight: 1.2,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {title}
      </div>
    </div>
  </div>
);

export const Weekly: React.FC<WeeklyProps> = ({ mode, heading, range, items, current, slot, cover }) => {
  if (mode === "thumb") {
    return (
      <AbsoluteFill>
        <Backdrop />
        <div style={{ position: "absolute", left: 70, top: 60, right: 70, display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontFamily, fontWeight: 900, fontSize: 34, letterSpacing: 6, color: RED }}>ITGONY · 주간 IT</div>
          <div style={{ fontFamily, fontWeight: 800, fontSize: 30, color: MUTED }}>{range}</div>
        </div>
        <div style={{ position: "absolute", left: 70, right: 70, top: 130, height: 6, background: INK }} />
        <div style={{ position: "absolute", left: 70, top: 190, right: 70, fontFamily: serifFamily, fontWeight: 900, fontSize: 118, lineHeight: 1.08, color: INK, whiteSpace: "pre-line" }}>
          {cover || heading}
        </div>
        <div style={{ position: "absolute", left: 70, right: 70, bottom: 56, display: "flex", gap: 18, flexWrap: "wrap" }}>
          {[...items].sort((a, b) => a.rank - b.rank).slice(0, 3).map((item) => (
            <div key={item.rank} style={{ fontFamily, fontWeight: 900, fontSize: 30, padding: "10px 22px", borderRadius: 999, background: INK, color: PAPER, maxWidth: 520, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {item.rank}위 {item.title}
            </div>
          ))}
        </div>
      </AbsoluteFill>
    );
  }

  const box = slot ?? { x: 90, y: 0, width: 608, height: 1080 };
  const left = box.x + box.width + 80;
  const size = items.length > 6 ? 40 : 46;

  return (
    <AbsoluteFill>
      <Backdrop />
      {/* 쇼츠가 얹힐 자리: 검은 테두리 카드 그림자 */}
      <div style={{ position: "absolute", left: box.x + 14, top: box.y + 14, width: box.width, height: box.height, background: INK, borderRadius: 0 }} />
      <div style={{ position: "absolute", left: box.x, top: box.y, width: box.width, height: box.height, background: CARD, border: `3px solid ${INK}` }} />
      <div style={{ position: "absolute", left, right: 80, top: 70 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontFamily, fontWeight: 900, fontSize: 30, letterSpacing: 6, color: RED }}>ITGONY · 주간 IT</div>
          <div style={{ fontFamily, fontWeight: 700, fontSize: 28, color: MUTED }}>{range}</div>
        </div>
        <div style={{ marginTop: 16, height: 5, background: INK }} />
        <div style={{ marginTop: 26, fontFamily: serifFamily, fontWeight: 900, fontSize: 84, lineHeight: 1.05, color: INK }}>{heading}</div>
        <div style={{ marginTop: 36, display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((item) => (
            <Row key={item.rank} rank={item.rank} title={item.title} series={item.series} hot={item.rank === current} size={size} />
          ))}
        </div>
      </div>
      <div style={{ position: "absolute", left, right: 80, bottom: 50, fontFamily, fontWeight: 800, fontSize: 28, color: MUTED }}>
        매일 저녁 6시 쇼츠 · 일요일 오전 11시 주간 정리
      </div>
    </AbsoluteFill>
  );
};
