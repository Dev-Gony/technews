import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { Chunk, Cut, Visual } from "../schema";
import { fontFamily, monoFamily, serifFamily } from "../theme";
import { Scene3DVisual } from "../Scene3DVisual";
import { IdeCodeVisual } from "./Editorial";

// news(크림 잡지) / explain(남색 다크) 스타일의 한 컷 = 한 페이지.
// 위에서부터: 섹션 번호 + 섹션 이름 → 큰 헤드라인 → 큰 카드 하나(숫자·비교·흐름·인용·코드…) → 자막.
// 예전 화면의 3D 아이콘·작은 박스는 쓰지 않는다. 카드가 없으면 헤드라인을 크게 가운데에.

type Style = "news" | "explain";

const P = {
  news: {
    ink: "#15130F",
    muted: "#6E675B",
    faint: "#8A8376",
    accent: "#C8402F",
    card: "#FFFDF7",
    cardBorder: "2px solid #15130F",
    cardShadow: "12px 12px 0 #15130F",
    sub: "#ECE6D8",
    subText: "#6E675B",
    hot: "#15130F",
    hotText: "#F4EFE3",
    hotAccent: "#FF6A52",
    line: "rgba(21,19,15,0.18)",
    head: serifFamily,
    big: serifFamily,
  },
  explain: {
    ink: "#E8ECF5",
    muted: "#9AA4B8",
    faint: "#5E6880",
    accent: "#F7B955",
    card: "rgba(17,24,39,0.92)",
    cardBorder: "1.5px solid rgba(255,255,255,0.14)",
    cardShadow: "0 40px 120px rgba(0,0,0,0.55), 0 0 0 1px rgba(76,141,255,0.10)",
    sub: "rgba(255,255,255,0.05)",
    subText: "#9AA4B8",
    hot: "rgba(76,141,255,0.14)",
    hotText: "#E8ECF5",
    hotAccent: "#F7B955",
    line: "rgba(232,236,245,0.10)",
    head: fontFamily,
    big: fontFamily,
  },
} as const;

type Palette = (typeof P)[Style];

// 화면 자리 (1080x1920, 아래 300px는 YouTube 버튼·제목에 가려진다)
const SIDE = 80;
const WIDTH = 1080 - SIDE * 2;
const POS = {
  news: { kicker: 252, heading: 318, card: 660, cardHeight: 540, caption: 1268 },
  explain: { kicker: 372, heading: 430, card: 700, cardHeight: 520, caption: 1290 },
};

const ease = Easing.bezier(0.16, 1, 0.3, 1);
const rise = (frame: number, start: number, length = 10) =>
  interpolate(frame, [start, start + length], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

// 헤드라인에서 강조 단어(대본 emphasis)와 숫자가 든 어절을 강조색으로
const accentWords = (text: string, emphasis: string[], color: string) => {
  const marks = emphasis.filter((word) => word && text.includes(word));
  const pattern = marks.length ? new RegExp(`(${marks.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`) : null;

  return text.split(/(\s+)/).flatMap((word, index) => {
    if (/\d/.test(word)) {
      return [
        <span key={index} style={{ color }}>
          {word}
        </span>,
      ];
    }

    if (!pattern) {
      return [word];
    }

    return word.split(pattern).map((piece, pieceIndex) =>
      marks.includes(piece) ? (
        <span key={`${index}-${pieceIndex}`} style={{ color }}>
          {piece}
        </span>
      ) : (
        piece
      ),
    );
  });
};

// 한글 글자 폭 ≈ 1em: 가장 긴 줄이 width 안에 들어가는 크기
// 숫자·영문은 굵은 명조에서 0.6em 안팎이지만 %·→ 같은 기호는 넓다. 넘치는 것보다 작은 게 낫다.
const charWidth = (char: string) => (/[%→←@#&MW]/.test(char) ? 1 : /[\x00-\x7F]/.test(char) ? 0.64 : 1);
const fitSize = (lines: string[], width: number, max: number, min: number) => {
  const longest = Math.max(...lines.map((line) => [...line].reduce((sum, char) => sum + charWidth(char), 0)), 1);
  return Math.max(min, Math.min(max, Math.floor(width / longest)));
};

// ---------------------------------------------------------------------------
// 카드

const CardBox: React.FC<{ p: Palette; children: React.ReactNode; padding?: number | string; height?: number | string }> = ({
  p,
  children,
  padding = 56,
  height = "100%",
}) => (
  <div
    style={{
      width: "100%",
      height,
      background: p.card,
      border: p.cardBorder,
      borderRadius: 30,
      boxShadow: p.cardShadow,
      padding,
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      overflow: "hidden",
    }}
  >
    {children}
  </div>
);

// 숫자 카운트업: "85%", "2.5배", "7.7tok/s" 같은 앞쪽 숫자만 센다
const CountUp: React.FC<{ value: string; progress: number }> = ({ value, progress }) => {
  const match = value.match(/^([^\d]*)(\d[\d,]*\.?\d*)(.*)$/);

  if (!match) {
    return <>{value}</>;
  }

  const target = Number(match[2].replace(/,/g, ""));
  const decimals = (match[2].split(".")[1] ?? "").length;
  const now = (target * progress).toFixed(decimals);
  const withComma = match[2].includes(",") ? Number(now).toLocaleString("en-US") : now;

  return (
    <>
      {match[1]}
      {withComma}
      {match[3]}
    </>
  );
};

const NumberCard: React.FC<{ visual: Visual; p: Palette; frame: number }> = ({ visual, p, frame }) => {
  const value = visual.value ?? "";
  const size = fitSize([value], WIDTH - 112, 230, 110);

  return (
    <CardBox p={p}>
      <div style={{ fontFamily: p.big, fontWeight: 900, fontSize: size, lineHeight: 1, color: p.accent, letterSpacing: -4 }}>
        <CountUp value={value} progress={rise(frame, 4, 22)} />
      </div>
      {visual.label ? (
        <div style={{ marginTop: 34, fontFamily, fontWeight: 700, fontSize: 46, color: p.muted, opacity: rise(frame, 14) }}>{visual.label}</div>
      ) : null}
    </CardBox>
  );
};

const SidePanel: React.FC<{ title: string; value: string; hot: boolean; p: Palette; show: number }> = ({ title, value, hot, p, show }) => (
  <div
    style={{
      flex: 1,
      borderRadius: 22,
      background: hot ? p.hot : p.sub,
      border: hot && p === P.explain ? "2px solid rgba(110,168,255,0.6)" : "none",
      padding: "40px 36px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
      opacity: show,
      translate: `0px ${interpolate(show, [0, 1], [30, 0])}px`,
    }}
  >
    <div style={{ fontFamily, fontWeight: 700, fontSize: 36, lineHeight: 1.3, color: hot ? p.hotAccent : p.subText, wordBreak: "keep-all" }}>{title}</div>
    <div
      style={{
        fontFamily: p.big,
        fontWeight: 900,
        fontSize: fitSize([value], 330, 130, 54),
        lineHeight: 1.05,
        color: hot ? p.hotAccent : p.faint,
        wordBreak: "keep-all",
      }}
    >
      {value}
    </div>
  </div>
);

const BeforeAfterCard: React.FC<{ visual: Visual; p: Palette; frame: number }> = ({ visual, p, frame }) => (
  <CardBox p={p} padding={40}>
    <div style={{ display: "flex", gap: 28, height: "100%" }}>
      <SidePanel title={visual.before?.title ?? "전"} value={visual.before?.value ?? ""} hot={false} p={p} show={rise(frame, 2)} />
      <SidePanel title={visual.after?.title ?? "후"} value={visual.after?.value ?? ""} hot p={p} show={rise(frame, 12)} />
    </div>
  </CardBox>
);

const BarsCard: React.FC<{ visual: Visual; p: Palette; frame: number }> = ({ visual, p, frame }) => {
  const bars = (visual.bars ?? []).slice(0, 4);
  const max = Math.max(...bars.map((bar) => bar.value), 1);
  // 강조할 막대: focus가 있으면 그것(예: AI 대결의 더 빠른 쪽), 없으면 가장 큰 값
  const top = visual.focus ?? bars.reduce((best, bar, index) => (bar.value > bars[best].value ? index : best), 0);

  return (
    <CardBox p={p}>
      {visual.label ? <div style={{ fontFamily, fontWeight: 700, fontSize: 32, color: p.faint, marginBottom: 30, letterSpacing: 2 }}>{visual.label}</div> : null}
      <div style={{ display: "flex", flexDirection: "column", gap: 34 }}>
        {bars.map((bar, index) => {
          const grow = rise(frame, 4 + index * 5, 16);
          return (
            <div key={index}>
              <div style={{ display: "flex", justifyContent: "space-between", fontFamily, fontWeight: 900, fontSize: 40, color: p.ink, marginBottom: 12 }}>
                <span>{bar.label}</span>
                <span style={{ color: index === top ? p.accent : p.muted }}>{bar.display}</span>
              </div>
              <div style={{ height: 30, borderRadius: 15, background: p.sub }}>
                <div style={{ height: "100%", width: `${(bar.value / max) * 100 * grow}%`, borderRadius: 15, background: index === top ? p.accent : p.faint }} />
              </div>
            </div>
          );
        })}
      </div>
    </CardBox>
  );
};

// 단계·구조도: 번호 매긴 줄. 마지막(또는 focus) 줄을 강조
const StepsCard: React.FC<{ items: string[]; focus: number; p: Palette; frame: number; arrows: boolean }> = ({ items, focus, p, frame, arrows }) => {
  const rows = items.slice(0, 4);
  // 화살표가 있는 3~4단계는 기본 크기로 쌓으면 카드(520~540px)를 넘어 위아래가 잘린다 → 촘촘하게
  const compact = arrows && rows.length >= 3;
  const size = fitSize(rows, WIDTH - 260, compact ? 44 : 52, 34);

  return (
    <CardBox p={p} padding={compact ? "30px 48px" : "44px 48px"}>
      <div style={{ display: "flex", flexDirection: "column", gap: compact ? 0 : arrows ? 14 : 22 }}>
        {rows.map((item, index) => {
          const show = rise(frame, 2 + index * 6);
          const hot = index === focus;
          return (
            <div key={index}>
              {arrows && index > 0 ? (
                <div
                  style={{
                    fontFamily: `${monoFamily}, ${fontFamily}`,
                    fontSize: compact ? 24 : 30,
                    lineHeight: compact ? 1 : undefined,
                    color: p.faint,
                    paddingLeft: 30,
                    margin: compact ? "4px 0" : "0 0 10px",
                    opacity: show,
                  }}
                >
                  ↓
                </div>
              ) : null}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 30,
                  padding: compact ? "16px 30px" : "22px 30px",
                  borderRadius: 18,
                  background: hot ? p.hot : p.sub,
                  border: hot && p === P.explain ? "2px solid rgba(110,168,255,0.6)" : "none",
                  opacity: show,
                  translate: `${interpolate(show, [0, 1], [40, 0])}px 0px`,
                }}
              >
                <div style={{ fontFamily: p === P.news ? serifFamily : `${monoFamily}, ${fontFamily}`, fontWeight: 900, fontSize: compact ? 38 : 44, color: hot ? p.hotAccent : p.faint, minWidth: 54 }}>
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div style={{ fontFamily, fontWeight: 900, fontSize: size, color: hot ? p.hotText : p.ink, wordBreak: "keep-all", lineHeight: 1.25 }}>{item}</div>
              </div>
            </div>
          );
        })}
      </div>
    </CardBox>
  );
};

// 핵심어가 하나뿐일 때: 큰 카드 가운데 한 줄만 있으면 비어 보인다.
// 카드를 낮추고, 위에 "KEYWORD" 라벨, 단어 아래에 강조색 밑줄이 그어지는 한 장면으로.
const SingleKeywordCard: React.FC<{ word: string; p: Palette; frame: number }> = ({ word, p, frame }) => {
  const size = fitSize([word], WIDTH - 140, 132, 64);
  const show = rise(frame, 2, 12);
  const underline = rise(frame, 10, 14);
  const news = p === P.news;

  return (
    <CardBox p={p} height="74%" padding="46px 56px 52px">
      <div style={{ display: "flex", alignItems: "center", gap: 16, opacity: rise(frame, 0) }}>
        <span style={{ width: 40, height: 4, background: p.accent }} />
        <span style={{ fontFamily: `${monoFamily}, ${fontFamily}`, fontWeight: 700, fontSize: 30, letterSpacing: 4, color: news ? p.accent : "#6EA8FF" }}>
          KEYWORD
        </span>
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div
          style={{
            display: "inline-flex",
            flexDirection: "column",
            alignItems: "stretch",
            opacity: show,
            translate: `0px ${interpolate(show, [0, 1], [24, 0])}px`,
          }}
        >
          <div style={{ fontFamily: p.big, fontWeight: 900, fontSize: size, lineHeight: 1.15, color: p.ink, wordBreak: "keep-all", textAlign: "center" }}>
            {word}
          </div>
          <div
            style={{
              marginTop: 18,
              height: Math.max(8, Math.round(size / 11)),
              borderRadius: 4,
              background: p.accent,
              transformOrigin: "left center",
              scale: `${underline} 1`,
            }}
          />
        </div>
      </div>
    </CardBox>
  );
};

// 핵심어: 큰 글씨 줄 (작은 알약 X)
const KeywordsCard: React.FC<{ items: string[]; p: Palette; frame: number }> = ({ items, p, frame }) => {
  const rows = items.slice(0, 3);

  if (rows.length === 1) {
    return <SingleKeywordCard word={rows[0]} p={p} frame={frame} />;
  }

  const size = fitSize(rows, WIDTH - 200, 76, 44);

  return (
    <CardBox p={p}>
      <div style={{ display: "flex", flexDirection: "column", gap: 34, alignItems: "flex-start" }}>
        {rows.map((item, index) => {
          const show = rise(frame, 2 + index * 7);
          return (
            <div
              key={index}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 26,
                opacity: show,
                translate: `0px ${interpolate(show, [0, 1], [24, 0])}px`,
              }}
            >
              <div style={{ width: 18, height: 18, borderRadius: 4, background: p.accent, flexShrink: 0 }} />
              <div
                style={{
                  fontFamily,
                  fontWeight: 900,
                  fontSize: size,
                  lineHeight: 1.2,
                  color: p.ink,
                  wordBreak: "keep-all",
                }}
              >
                {item}
              </div>
            </div>
          );
        })}
      </div>
    </CardBox>
  );
};

const QuoteCard: React.FC<{ visual: Visual; p: Palette; frame: number }> = ({ visual, p, frame }) => {
  const text = visual.quote ?? visual.value ?? "";
  const size = text.length > 40 ? 46 : text.length > 24 ? 54 : 64;

  return (
    <CardBox p={p}>
      <div style={{ fontFamily: serifFamily, fontWeight: 900, fontSize: 150, lineHeight: 0.6, color: p.accent, opacity: rise(frame, 0) }}>“</div>
      <div
        style={{
          marginTop: 24,
          fontFamily: p === P.news ? serifFamily : fontFamily,
          fontWeight: 700,
          fontSize: size,
          lineHeight: 1.45,
          color: p.ink,
          wordBreak: "keep-all",
          opacity: rise(frame, 4, 14),
        }}
      >
        {text}
      </div>
      {visual.label ? <div style={{ marginTop: 30, fontFamily, fontWeight: 700, fontSize: 32, color: p.faint, opacity: rise(frame, 12) }}>— {visual.label}</div> : null}
    </CardBox>
  );
};

// AI 대결 답 말풍선: 위에 AI 이름, 아래 말풍선에 실제 답이 타자 치듯 써진다 (battle.py)
const AI_COLORS: Record<string, string> = { Claude: "#D97757", Gemini: "#4C8DFF" };

const ChatCard: React.FC<{ visual: Visual; p: Palette; frame: number; sceneFrames: number }> = ({ visual, p, frame, sceneFrames }) => {
  const name = visual.label ?? "";
  const color = AI_COLORS[name] ?? p.accent;
  const text = visual.quote ?? "";
  const typed = Math.round(interpolate(frame, [6, Math.max(sceneFrames * 0.6, 12)], [0, text.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const size = text.length > 50 ? 48 : text.length > 28 ? 56 : 66;

  return (
    <CardBox p={p} padding={44}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, opacity: rise(frame, 0) }}>
        <div style={{ width: 64, height: 64, borderRadius: 999, background: color, display: "flex", alignItems: "center", justifyContent: "center", color: "#FFFFFF", fontFamily, fontWeight: 900, fontSize: 34 }}>
          {name.slice(0, 1)}
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontFamily, fontWeight: 900, fontSize: 44, color: p.ink, lineHeight: 1.1 }}>{name}</div>
          {visual.value ? <div style={{ fontFamily, fontWeight: 600, fontSize: 26, color: p.faint }}>{visual.value}</div> : null}
        </div>
      </div>
      <div
        style={{
          marginTop: 30,
          padding: "28px 34px",
          borderRadius: 28,
          borderTopLeftRadius: 6,
          background: p.sub,
          borderLeft: `8px solid ${color}`,
          fontFamily,
          fontWeight: 800,
          fontSize: size,
          lineHeight: 1.4,
          color: p.ink,
          wordBreak: "keep-all",
          minHeight: size * 1.4 * 2 + 56,
        }}
      >
        {text.slice(0, typed)}
        {typed < text.length ? <span style={{ color }}>▍</span> : null}
      </div>
    </CardBox>
  );
};

// 비유: "무엇 → 실제로는" 두 칸 표
const PairsCard: React.FC<{ visual: Visual; p: Palette; frame: number }> = ({ visual, p, frame }) => {
  const rooms = (visual.rooms ?? []).slice(0, 3);

  return (
    <CardBox p={p} padding="44px 48px">
      <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
        {rooms.map((room, index) => {
          const show = rise(frame, 2 + index * 7);
          return (
            <div
              key={index}
              style={{ display: "flex", alignItems: "center", gap: 24, opacity: show, translate: `${interpolate(show, [0, 1], [40, 0])}px 0px` }}
            >
              <div style={{ flex: 1, padding: "26px 28px", borderRadius: 18, background: p.sub, fontFamily, fontWeight: 900, fontSize: 44, color: p.ink, wordBreak: "keep-all" }}>
                {room.place}
              </div>
              <div style={{ fontFamily: `${monoFamily}, ${fontFamily}`, fontSize: 44, color: p.accent }}>→</div>
              <div style={{ flex: 1, fontFamily: `${monoFamily}, ${fontFamily}`, fontWeight: 700, fontSize: 40, color: p.accent, wordBreak: "break-all" }}>{room.actual}</div>
            </div>
          );
        })}
      </div>
    </CardBox>
  );
};

const QuestionCard: React.FC<{ visual: Visual; p: Palette; frame: number }> = ({ visual, p, frame }) => (
  <CardBox p={p}>
    <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
      <div style={{ fontFamily: p.big, fontWeight: 900, fontSize: 260, lineHeight: 1, color: p.accent, scale: String(interpolate(rise(frame, 0, 12), [0, 1], [0.6, 1])) }}>?</div>
      <div style={{ fontFamily, fontWeight: 900, fontSize: 58, lineHeight: 1.3, color: p.ink, wordBreak: "keep-all", opacity: rise(frame, 6) }}>
        {visual.value ?? visual.label ?? ""}
      </div>
    </div>
  </CardBox>
);

// 원문 이미지: 원문에 실린 실제 사진·화면을 카드에 꽉 차게(잘리지 않게) 띄우고 천천히 다가간다. 아래에 출처.
const ImageCard: React.FC<{ visual: Visual; p: Palette; frame: number; sceneFrames: number }> = ({ visual, p, frame, sceneFrames }) => {
  const zoom = interpolate(frame, [0, Math.max(sceneFrames, 1)], [1, 1.06], { extrapolateRight: "clamp" });
  const source = [visual.label, visual.value].filter(Boolean).join(" · ");

  return (
    <CardBox p={p} padding={18}>
      <div style={{ position: "relative", flex: 1, borderRadius: 18, overflow: "hidden", background: p.sub }}>
        <Img
          src={staticFile(visual.src ?? "")}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", scale: String(zoom), opacity: rise(frame, 2, 10) }}
        />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, paddingTop: 14, paddingLeft: 8, fontFamily, fontWeight: 800, fontSize: 30, color: p.subText }}>
        <span style={{ color: p.accent, flexShrink: 0, whiteSpace: "nowrap" }}>원문 이미지</span>
        {source ? <span style={{ minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{source}</span> : null}
      </div>
    </CardBox>
  );
};

// 훅 그림 자리 (제목이 위로 올라간 아래, 자막 위)
const HOOK_AREA = { top: 650, bottom: 1160 };
const HOOK_CAPTION = 1260;

// 카드 종류 고르기. 그릴 게 없으면 null (헤드라인만 크게)
const cardFor = (visual: Visual, p: Palette, frame: number, sceneFrames: number) => {
  switch (visual.type) {
    case "number":
    case "scale":
      return visual.value || visual.count ? <NumberCard visual={{ ...visual, value: visual.value ?? String(visual.count) }} p={p} frame={frame} /> : null;
    case "beforeafter":
      return visual.before && visual.after ? <BeforeAfterCard visual={visual} p={p} frame={frame} /> : null;
    case "compare":
      return visual.bars?.length ? <BarsCard visual={visual} p={p} frame={frame} /> : null;
    case "flow":
      return visual.items?.length ? <StepsCard items={visual.items} focus={visual.items.length - 1} p={p} frame={frame} arrows={false} /> : null;
    case "diagram": {
      const items = (visual.nodes ?? []).map((node) => node.label);
      return items.length ? <StepsCard items={items} focus={visual.focus ?? items.length - 1} p={p} frame={frame} arrows /> : null;
    }
    case "keywords":
      return visual.items?.length ? <KeywordsCard items={visual.items} p={p} frame={frame} /> : null;
    case "quote":
      return visual.quote || visual.value ? <QuoteCard visual={visual} p={p} frame={frame} /> : null;
    case "metaphor":
      return visual.rooms?.length ? <PairsCard visual={visual} p={p} frame={frame} /> : null;
    case "question":
      return <QuestionCard visual={visual} p={p} frame={frame} />;
    case "code":
      return visual.code ? <IdeCodeVisual visual={visual} sceneFrames={sceneFrames} bare /> : null;
    case "image":
      return visual.src ? <ImageCard visual={visual} p={p} frame={frame} sceneFrames={sceneFrames} /> : null;
    case "chat":
      return visual.quote ? <ChatCard visual={visual} p={p} frame={frame} sceneFrames={sceneFrames} /> : null;
    default:
      return null;
  }
};

// ---------------------------------------------------------------------------
// 자막: 한 번에 한 덩어리, 강조 덩어리는 강조색

const PageCaption: React.FC<{ chunks: Chunk[]; style: Style; top: number }> = ({ chunks, style, top }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = P[style];
  const chunk = chunks.find((item) => frame >= item.from && frame < item.from + item.durationInFrames);

  if (!chunk) {
    return null;
  }

  const pop = spring({ frame: frame - chunk.from, fps, config: { damping: 16, stiffness: 260 } });
  const size = fitSize([chunk.text], WIDTH, 74, 50);

  return (
    <div
      style={{
        position: "absolute",
        top,
        left: SIDE / 2,
        right: SIDE / 2,
        textAlign: "center",
        fontFamily,
        fontWeight: 900,
        fontSize: size,
        lineHeight: 1.3,
        color: chunk.emphasis ? p.accent : p.ink,
        textShadow: style === "explain" ? "0 4px 24px rgba(0,0,0,0.8)" : "none",
        scale: String(interpolate(pop, [0, 1], [0.92, 1])),
        opacity: interpolate(pop, [0, 0.4], [0, 1], { extrapolateRight: "clamp" }),
        wordBreak: "keep-all",
      }}
    >
      {chunk.text}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 페이지

export const EditorialPage: React.FC<{ cut: Cut; index: number; style: Style; emphasis: string[] }> = ({ cut, index, style, emphasis }) => {
  const frame = useCurrentFrame();
  const p = P[style];
  const pos = POS[style];
  const hook = index === 0;
  // 훅에 그림(원문 이미지·3D 장면)이 있으면 제목 아래에 바로 보여 준다: 첫 1초에 글자만 있으면 넘긴다
  const hookVisual = hook && (cut.visual.type === "image" || cut.visual.type === "scene3d") ? cut.visual : null;
  const card = hook ? null : cardFor(cut.visual, p, frame, cut.durationInFrames);
  // 3D 꼬마 캐릭터 장면: 카드 대신 헤드라인 아래부터 자막 위까지 크게
  const scene3d = !hook && cut.visual.type === "scene3d" && Boolean(cut.visual.scene);
  const heading = (cut.heading ?? "").split("\n").slice(0, 2).filter(Boolean);
  const section = cut.section ?? "";
  const number = String(index).padStart(2, "0");
  const show = rise(frame, 0, 8);
  const cardShow = rise(frame, 4, 12);
  // 카드 위로 천천히 다가가는 카메라 (컷 내내)
  const push = interpolate(frame, [0, Math.max(cut.durationInFrames, 1)], [1, 1.035], { extrapolateRight: "clamp" });
  const headingTop = card || scene3d ? pos.heading : pos.card + 60;
  const headingSize = scene3d
    ? fitSize(heading, WIDTH, style === "news" ? 84 : 76, 56)
    : card
      ? fitSize(heading, style === "news" ? WIDTH : WIDTH, style === "news" ? 96 : 88, 60)
      : fitSize(heading, WIDTH, 140, 80);
  const captionTop = pos.caption;
  const sceneArea = {
    top: heading.length ? Math.round(headingTop + heading.length * headingSize * 1.18 + 40) : pos.heading + 20,
    bottom: captionTop - 30,
  };

  return (
    <AbsoluteFill>
      {!hook && section ? (
        <div
          style={{
            position: "absolute",
            top: pos.kicker,
            left: SIDE,
            right: SIDE,
            display: "flex",
            alignItems: "center",
            justifyContent: style === "news" ? "flex-start" : "center",
            gap: 20,
            opacity: show,
            translate: `0px ${interpolate(show, [0, 1], [16, 0])}px`,
          }}
        >
          {style === "news" ? (
            <>
              <span style={{ fontFamily: serifFamily, fontWeight: 900, fontSize: 42, color: p.accent }}>{number}</span>
              <span style={{ width: 64, height: 3, background: p.accent }} />
              <span style={{ fontFamily, fontWeight: 700, fontSize: 36, color: p.muted }}>{section}</span>
            </>
          ) : (
            <span style={{ fontFamily: `${monoFamily}, ${fontFamily}`, fontWeight: 700, fontSize: 32, color: "#6EA8FF" }}>
              <span style={{ color: p.faint }}>{"// "}</span>
              {number} · {section}
            </span>
          )}
        </div>
      ) : null}
      {!hook && heading.length ? (
        <div
          style={{
            position: "absolute",
            top: headingTop,
            left: SIDE,
            right: SIDE,
            textAlign: style === "news" ? "left" : "center",
            fontFamily: p.head,
            fontWeight: 900,
            fontSize: headingSize,
            lineHeight: 1.18,
            letterSpacing: style === "news" ? -2 : -1,
            color: p.ink,
            wordBreak: "keep-all",
            opacity: show,
            translate: `0px ${interpolate(show, [0, 1], [24, 0])}px`,
          }}
        >
          {heading.map((line, lineIndex) => (
            <div key={lineIndex}>{accentWords(line, emphasis, p.accent)}</div>
          ))}
        </div>
      ) : null}
      {card ? (
        <div
          style={{
            position: "absolute",
            top: pos.card,
            left: SIDE,
            width: WIDTH,
            height: pos.cardHeight,
            display: "flex",
            alignItems: "center",
            opacity: cardShow,
            translate: `0px ${interpolate(cardShow, [0, 1], [50, 0])}px`,
            scale: String(push),
          }}
        >
          {card}
        </div>
      ) : null}
      {scene3d ? (
        <Scene3DVisual
          visual={cut.visual}
          sceneFrames={cut.durationInFrames}
          chunks={cut.chunks}
          area={sceneArea}
          accent={p.accent}
          accentText={style === "news" ? "#FFFFFF" : "#15130F"}
          dimAmount={style === "news" ? 0.3 : 0.6}
        />
      ) : null}
      {hookVisual?.type === "scene3d" && hookVisual.scene ? (
        <Scene3DVisual
          visual={{ ...hookVisual, beats: [] }}
          sceneFrames={cut.durationInFrames}
          chunks={cut.chunks}
          area={HOOK_AREA}
          accent={p.accent}
          accentText={style === "news" ? "#FFFFFF" : "#15130F"}
          dimAmount={0}
          overviewZoom={1.2}
        />
      ) : null}
      {hookVisual?.type === "image" && hookVisual.src ? (
        <div
          style={{
            position: "absolute",
            top: HOOK_AREA.top,
            left: SIDE,
            right: SIDE,
            height: HOOK_AREA.bottom - HOOK_AREA.top,
            opacity: rise(frame, 0, 6),
            scale: String(interpolate(frame, [0, 8], [1.08, 1], { extrapolateRight: "clamp" })),
          }}
        >
          <ImageCard visual={hookVisual} p={p} frame={frame} sceneFrames={cut.durationInFrames} />
        </div>
      ) : null}
      <PageCaption chunks={cut.chunks} style={style} top={hook ? (hookVisual ? HOOK_CAPTION : 1180) : captionTop} />
    </AbsoluteFill>
  );
};
