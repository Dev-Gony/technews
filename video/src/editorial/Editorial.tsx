import { createContext, useContext } from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Visual } from "../schema";
import { colors, fontFamily, layout, monoFamily, serifFamily, type StyleName } from "../theme";
import { Panel, pop } from "../visualKit";

// news(크림 잡지) / explain(남색 다크 + 코드 창) 스타일 전용 화면 요소.
// 기존(classic) 화면은 Short.tsx 그대로 두고, 스타일이 news/explain일 때만 아래 컴포넌트로 바꿔 끼운다.

export const StyleContext = createContext<StyleName>("classic");
export const useShortStyle = () => useContext(StyleContext);
export const isEditorial = (style?: StyleName): style is "news" | "explain" => style === "news" || style === "explain";

const NEWS_RED = "#C8402F";
const EXPLAIN_BLUE = "#6EA8FF";
const EXPLAIN_GOLD = "#F7B955";

// 숫자가 든 어절만 강조색
const accentDigits = (line: string, color: string) =>
  line.split(/(\s+)/).map((word, index) =>
    /\d/.test(word) ? (
      <span key={index} style={{ color }}>
        {word}
      </span>
    ) : (
      word
    ),
  );

// ---------------------------------------------------------------------------
// 배경

// news: 크림 종이 + 위쪽에서 들어오는 흰 빛 + 아주 옅은 종이 결
const NewsBackdrop: React.FC = () => (
  <AbsoluteFill>
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 90% 45% at 50% 0%, rgba(255,255,255,0.75), transparent 70%)" }} />
    <AbsoluteFill
      style={{
        backgroundImage:
          "repeating-linear-gradient(90deg, rgba(21,19,15,0.018) 0px, rgba(21,19,15,0.018) 1px, transparent 1px, transparent 6px)",
      }}
    />
  </AbsoluteFill>
);

// explain: 남색 + 격자 + 천천히 떠다니는 파란 빛 + 점 입자
const ExplainBackdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const x = 540 + Math.sin(frame / 90) * 120;
  const y = 760 + Math.cos(frame / 120) * 140;
  const dots = Array.from({ length: 22 }, (_, i) => {
    const seed = (i * 97) % 101;
    return {
      left: (seed * 10.7 + i * 37) % 1080,
      top: 380 + ((seed * 13 + i * 71) % 1100),
      size: 4 + (i % 3) * 2,
      color: i % 5 === 0 ? EXPLAIN_GOLD : i % 2 ? EXPLAIN_BLUE : "#FFFFFF",
      phase: i * 0.7,
    };
  });

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          translate: `0px ${-(frame * 0.4) % 60}px`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 1100,
          height: 1100,
          left: x - 550,
          top: y - 550,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(76,141,255,0.22) 0%, transparent 62%)",
        }}
      />
      {dots.map((dot, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: dot.left,
            top: dot.top + Math.sin(frame / 40 + dot.phase) * 14,
            width: dot.size,
            height: dot.size,
            borderRadius: "50%",
            background: dot.color,
            opacity: 0.25 + 0.25 * Math.sin(frame / 30 + dot.phase),
          }}
        />
      ))}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(0,0,0,0.5) 100%)" }} />
    </AbsoluteFill>
  );
};

export const EditorialBackdrop: React.FC<{ style: "news" | "explain" }> = ({ style }) =>
  style === "news" ? <NewsBackdrop /> : <ExplainBackdrop />;

// ---------------------------------------------------------------------------
// 상단 머리 (채널·출처·진행 막대)

const Progress: React.FC<{ top: number; color: string; track: string }> = ({ top, color, track }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width } = useVideoConfig();

  return (
    <div style={{ position: "absolute", top, left: layout.side, width: width - layout.side * 2, height: 4, background: track }}>
      <div style={{ height: "100%", width: `${(frame / Math.max(durationInFrames - 1, 1)) * 100}%`, background: color }} />
    </div>
  );
};

// news: 잡지 머리 — "ITGONY · AI NEWS" + 출처, 그 아래 두 줄 선(굵은 선이 진행 막대)
const NewsChrome: React.FC<{ channel: string; source: string }> = ({ channel, source }) => {
  const { width } = useVideoConfig();

  return (
    <AbsoluteFill style={{ fontFamily }}>
      <div
        style={{
          position: "absolute",
          top: 140,
          left: layout.side,
          width: width - layout.side * 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          letterSpacing: 4,
          fontWeight: 700,
          color: colors.faint,
        }}
      >
        <span style={{ fontSize: 30 }}>
          <span style={{ color: NEWS_RED, fontWeight: 900 }}>{channel.toUpperCase()}</span> · AI NEWS
        </span>
        <span style={{ fontSize: 24, letterSpacing: 0, fontWeight: 500 }}>{source}</span>
      </div>
      <Progress top={196} color={colors.text} track="rgba(21,19,15,0.18)" />
      <div style={{ position: "absolute", top: 206, left: layout.side, width: width - layout.side * 2, height: 1, background: colors.text }} />
    </AbsoluteFill>
  );
};

// explain: 터미널 프롬프트처럼 "~/itgony" + 출처
const ExplainChrome: React.FC<{ channel: string; source: string }> = ({ channel, source }) => {
  const { width } = useVideoConfig();

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: 140,
          left: layout.side,
          width: width - layout.side * 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          color: colors.faint,
        }}
      >
        <span style={{ fontFamily: monoFamily, fontSize: 30, fontWeight: 700 }}>
          <span style={{ color: "#28C840" }}>~/</span>
          <span style={{ color: colors.muted }}>{channel.toLowerCase()}</span>
        </span>
        <span style={{ fontFamily, fontSize: 24, fontWeight: 500 }}>{source}</span>
      </div>
      <Progress top={196} color={EXPLAIN_BLUE} track="rgba(232,236,245,0.08)" />
    </AbsoluteFill>
  );
};

export const EditorialChrome: React.FC<{ style: "news" | "explain"; channel: string; source: string }> = ({ style, ...props }) =>
  style === "news" ? <NewsChrome {...props} /> : <ExplainChrome {...props} />;

// ---------------------------------------------------------------------------
// 제목(cover): 첫 컷 동안 화면 가운데 크게(훅) → 상단에 고정

// news: 왼쪽 정렬 명조. 위로 올라가면 빨간 줄 + 큰 제목 (잡지 헤드라인)
const NewsCover: React.FC<{ text: string; heroFrames: number }> = ({ text, heroFrames }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const lines = text.split("\n").slice(0, 2);
  const longest = Math.max(...lines.map((line) => line.length), 1);
  const shrink = interpolate(frame, [heroFrames - 10, heroFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });
  const rise = interpolate(frame, [0, 10], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const heroSize = longest > 9 ? 120 : 140;
  const headerSize = longest > 10 ? 60 : 68;

  return (
    <div
      style={{
        position: "absolute",
        top: interpolate(shrink, [0, 1], [520, 240]) + (shrink > 0 ? 0 : rise),
        left: layout.side,
        width: width - layout.side * 2,
        opacity: interpolate(frame, [0, 6], [0, 1], { extrapolateRight: "clamp" }),
      }}
    >
      <div
        style={{
          width: interpolate(frame, [4, 16], [0, 90], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          height: 5,
          background: NEWS_RED,
          marginBottom: interpolate(shrink, [0, 1], [34, 18]),
        }}
      />
      <div
        style={{
          fontFamily: serifFamily,
          fontWeight: 900,
          fontSize: interpolate(shrink, [0, 1], [heroSize, headerSize]),
          lineHeight: 1.16,
          letterSpacing: -2,
          color: colors.text,
          wordBreak: "keep-all",
        }}
      >
        {lines.map((line, index) => (
          <div key={index}>{accentDigits(line, NEWS_RED)}</div>
        ))}
      </div>
    </div>
  );
};

// explain: 가운데 굵은 고딕 → 위로 올라가면 파란 알약 라벨 한 줄
const ExplainCover: React.FC<{ text: string; heroFrames: number }> = ({ text, heroFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lines = text.split("\n").slice(0, 2);
  const longest = Math.max(...lines.map((line) => line.length), 1);
  const toPill = interpolate(frame, [heroFrames - 10, heroFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });
  const slam = spring({ frame, fps, config: { damping: 14, stiffness: 180 } });
  const pillIn = spring({ frame: frame - heroFrames + 4, fps, config: { damping: 14, stiffness: 160 } });

  return (
    <AbsoluteFill>
      {toPill < 1 ? (
        <div
          style={{
            position: "absolute",
            top: 560,
            left: layout.side / 2,
            right: layout.side / 2,
            textAlign: "center",
            fontFamily,
            fontWeight: 900,
            fontSize: longest > 9 ? 116 : 136,
            lineHeight: 1.16,
            letterSpacing: -3,
            color: colors.text,
            wordBreak: "keep-all",
            opacity: 1 - toPill,
            scale: String(interpolate(slam, [0, 1], [1.25, 1]) * interpolate(toPill, [0, 1], [1, 0.6])),
            translate: `0px ${interpolate(toPill, [0, 1], [0, -300])}px`,
          }}
        >
          {lines.map((line, index) => (
            <div key={index}>{accentDigits(line, EXPLAIN_GOLD)}</div>
          ))}
        </div>
      ) : null}
      <div
        style={{
          position: "absolute",
          top: 262,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: pillIn,
          translate: `0px ${interpolate(pillIn, [0, 1], [-20, 0])}px`,
        }}
      >
        <div
          style={{
            padding: "16px 42px",
            borderRadius: 999,
            border: `2px solid rgba(110,168,255,0.7)`,
            background: "rgba(76,141,255,0.10)",
            color: "#9CC3FF",
            fontFamily,
            fontWeight: 700,
            fontSize: 40,
            whiteSpace: "nowrap",
          }}
        >
          {accentDigits(lines.join(" "), EXPLAIN_GOLD)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const EditorialCover: React.FC<{ style: "news" | "explain"; text: string; heroFrames: number }> = ({ style, ...props }) =>
  style === "news" ? <NewsCover {...props} /> : <ExplainCover {...props} />;

// ---------------------------------------------------------------------------
// 코드 창: macOS 창 + 문법 색 + 강조 줄 + 커서. 줄이 차례로 써지고, 끝나면 커서가 강조 줄로 가서 카메라가 그 줄로 다가간다.

const KEYWORDS = new Set(
  (
    "fn func function def class const let var return if else for while in of import from export async await try catch " +
    "errdefer defer pub struct enum interface type new self this public private static void int u8 i32 bool true false null nil " +
    "SELECT FROM WHERE ORDER BY LIMIT INSERT INTO UPDATE DELETE JOIN AND OR NOT AS GROUP CREATE TABLE INDEX"
  ).split(" "),
);

const SYNTAX = {
  keyword: "#C792EA",
  type: "#82AAFF",
  string: "#C3E88D",
  number: "#F78C6C",
  comment: "#637089",
  prompt: "#28C840",
  text: "#D6DEEB",
};

// 아주 단순한 문법 색칠: 주석·문자열·숫자·키워드·대문자로 시작하는 이름·쉘 프롬프트
const tokenize = (line: string): { text: string; color: string }[] => {
  const comment = line.match(/^(\s*)(\/\/|#(?!!)|--)(.*)$/);

  if (comment) {
    return [{ text: line, color: SYNTAX.comment }];
  }

  const prompt = line.match(/^(\s*)\$ (.*)$/);

  if (prompt) {
    return [
      { text: `${prompt[1]}$ `, color: SYNTAX.prompt },
      ...tokenize(prompt[2]),
    ];
  }

  const parts = line.split(/("[^"]*"|'[^']*'|`[^`]*`|\b\d[\d_.]*\b|[A-Za-z_][A-Za-z0-9_]*)/);

  return parts
    .filter((part) => part !== "")
    .map((part) => {
      if (/^["'`]/.test(part)) return { text: part, color: SYNTAX.string };
      if (/^\d/.test(part)) return { text: part, color: SYNTAX.number };
      if (KEYWORDS.has(part)) return { text: part, color: SYNTAX.keyword };
      if (/^[A-Z][a-z]/.test(part)) return { text: part, color: SYNTAX.type };
      return { text: part, color: SYNTAX.text };
    });
};

const LINE_HEIGHT = 58;

export const IdeCodeVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const lines = (visual.code ?? "").split("\n").slice(0, 8);
  const longest = Math.max(...lines.map((line) => [...line].length), 1);
  // 창 안(가로 약 820px)에 가장 긴 줄이 들어가게 글자 크기를 줄인다. (고정폭 글자 폭 ≈ 0.6em)
  const fontSize = Math.max(24, Math.min(36, Math.floor(820 / (longest * 0.6))));
  const highlight = visual.highlight && visual.highlight >= 1 && visual.highlight <= lines.length ? visual.highlight - 1 : -1;
  const typingEnd = Math.max(sceneFrames * 0.45, 12);
  const perLine = typingEnd / Math.max(lines.length, 1);
  const shown = pop(frame, 0, 12);
  const focus = highlight >= 0 ? pop(frame, typingEnd, 14) : 0;
  const filename = visual.label || (lines.some((line) => /^\s*\$ /.test(line)) ? "zsh" : "code");
  const rowTop = 72 + 34 + highlight * LINE_HEIGHT;

  return (
    <Panel>
      <div
        style={{
          width: "104%",
          borderRadius: 26,
          overflow: "hidden",
          background: "#111827",
          border: "1.5px solid rgba(255,255,255,0.14)",
          boxShadow: "0 40px 120px rgba(0,0,0,0.55), 0 0 0 1px rgba(76,141,255,0.10)",
          opacity: shown,
          translate: `0px ${interpolate(shown, [0, 1], [50, 0])}px`,
          // 강조 줄로 카메라가 다가간다 (Screen Studio 식 부드러운 줌)
          transformOrigin: `50% ${rowTop}px`,
          scale: String(interpolate(focus, [0, 1], [1, 1.12])),
          position: "relative",
        }}
      >
        <div
          style={{
            height: 72,
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: "0 30px",
            background: "#0E1422",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            position: "relative",
          }}
        >
          {["#FF5F57", "#FEBC2E", "#28C840"].map((color) => (
            <div key={color} style={{ width: 22, height: 22, borderRadius: 11, background: color }} />
          ))}
          <div style={{ position: "absolute", left: 0, right: 0, textAlign: "center", fontFamily: monoFamily, fontSize: 26, color: "#7D879C" }}>
            {filename}
          </div>
        </div>
        <div style={{ padding: "34px 0", fontFamily: `${monoFamily}, ${fontFamily}`, fontSize, lineHeight: `${LINE_HEIGHT}px` }}>
          {lines.map((line, index) => {
            const start = index * perLine;
            const chars = [...line];
            const typed = Math.round(
              interpolate(frame, [start, start + perLine], [0, chars.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            );
            const visible = chars.slice(0, typed).join("");
            const isHighlight = index === highlight;
            let used = 0;

            return (
              <div
                key={index}
                style={{
                  position: "relative",
                  padding: "0 44px",
                  whiteSpace: "pre",
                  minHeight: LINE_HEIGHT,
                  opacity: highlight >= 0 && !isHighlight ? interpolate(focus, [0, 1], [1, 0.45]) : 1,
                  background: isHighlight ? `rgba(247,185,85,${0.16 * focus})` : "transparent",
                  boxShadow: isHighlight ? `inset ${6 * focus}px 0 0 ${EXPLAIN_GOLD}` : "none",
                }}
              >
                {tokenize(line).map((token, tokenIndex) => {
                  const begin = used;
                  used += [...token.text].length;
                  const text = [...visible].slice(begin, used).join("");
                  return text ? (
                    <span key={tokenIndex} style={{ color: token.color }}>
                      {text}
                    </span>
                  ) : null;
                })}
                {typed < chars.length && frame >= start ? <span style={{ color: SYNTAX.text }}>▌</span> : null}
              </div>
            );
          })}
        </div>
        {highlight >= 0 ? (
          <svg
            viewBox="0 0 24 30"
            style={{
              position: "absolute",
              width: 44,
              height: 56,
              left: interpolate(focus, [0, 1], [900, 620]),
              top: interpolate(focus, [0, 1], [rowTop + 220, rowTop + 26]),
              opacity: interpolate(frame, [typingEnd - 6, typingEnd], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            }}
          >
            <path d="M2 2 L2 24 L8 18 L12 28 L16 26 L12 17 L20 17 Z" fill="#FFFFFF" stroke="#000000" strokeWidth="1.5" />
          </svg>
        ) : null}
      </div>
    </Panel>
  );
};

// ---------------------------------------------------------------------------
// 마무리

// explain: 터미널에 "$ itgony --next"가 타이핑되고 채널 소개가 뜬다
const ExplainOutro: React.FC<{ channel: string }> = ({ channel }) => {
  const frame = useCurrentFrame();
  const cover = interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const command = `${channel.toLowerCase()} --next`;
  const typed = Math.round(interpolate(frame, [6, 22], [0, command.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const line = interpolate(frame, [24, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cursorOn = Math.floor(frame / 12) % 2 === 0;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, opacity: cover, alignItems: "center", justifyContent: "center" }}>
      <ExplainBackdrop />
      <div
        style={{
          width: 900,
          marginTop: -160,
          borderRadius: 26,
          overflow: "hidden",
          background: "#111827",
          border: "1.5px solid rgba(255,255,255,0.14)",
          boxShadow: "0 40px 120px rgba(0,0,0,0.55)",
        }}
      >
        <div style={{ height: 72, display: "flex", alignItems: "center", gap: 16, padding: "0 30px", background: "#0E1422" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((color) => (
            <div key={color} style={{ width: 22, height: 22, borderRadius: 11, background: color }} />
          ))}
        </div>
        <div style={{ padding: "40px 44px", fontFamily: monoFamily, fontSize: 52, color: SYNTAX.text, whiteSpace: "pre" }}>
          <span style={{ color: SYNTAX.prompt }}>$ </span>
          {command.slice(0, typed)}
          <span style={{ opacity: cursorOn ? 1 : 0 }}>▌</span>
        </div>
      </div>
      <div
        style={{
          marginTop: 60,
          fontFamily,
          fontWeight: 900,
          fontSize: 50,
          color: colors.text,
          textAlign: "center",
          lineHeight: 1.4,
          opacity: line,
          translate: `0px ${interpolate(line, [0, 1], [16, 0])}px`,
        }}
      >
        AI·개발 뉴스,
        <br />
        출근·점심·퇴근길에 <span style={{ color: EXPLAIN_GOLD }}>{channel}</span>
      </div>
    </AbsoluteFill>
  );
};

// news: 크림 종이 위 "IT." 명조 로고 + 소개 (기존 마무리와 같은 구성, 잡지 색)
const NewsOutro: React.FC<{ channel: string }> = ({ channel }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cover = interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const logo = spring({ frame: frame - 4, fps, config: { damping: 12, stiffness: 140 } });
  const dot = spring({ frame: frame - 12, fps, config: { damping: 8, stiffness: 220 } });
  const line = interpolate(frame, [14, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, opacity: cover, alignItems: "center", justifyContent: "center" }}>
      <NewsBackdrop />
      <div style={{ width: 120, height: 5, background: NEWS_RED, marginTop: -160, marginBottom: 40, scale: String(line) }} />
      <div
        style={{
          fontFamily: serifFamily,
          fontWeight: 900,
          fontSize: 240,
          lineHeight: 1,
          letterSpacing: -4,
          color: colors.text,
          opacity: interpolate(logo, [0, 0.4], [0, 1], { extrapolateRight: "clamp" }),
          scale: String(interpolate(logo, [0, 1], [0.85, 1])),
        }}
      >
        IT
        <span style={{ color: NEWS_RED, display: "inline-block", scale: String(dot) }}>.</span>
      </div>
      <div style={{ marginTop: 30, fontFamily, fontWeight: 900, fontSize: 44, letterSpacing: 6, color: colors.text, opacity: line }}>
        {channel.toUpperCase()} · AI NEWS
      </div>
      <div style={{ marginTop: 18, fontFamily, fontWeight: 700, fontSize: 36, color: colors.muted, opacity: line }}>
        AI·개발 뉴스, 출근·점심·퇴근길에
      </div>
    </AbsoluteFill>
  );
};

export const EditorialOutro: React.FC<{ style: "news" | "explain"; channel: string }> = ({ style, channel }) =>
  style === "news" ? <NewsOutro channel={channel} /> : <ExplainOutro channel={channel} />;
