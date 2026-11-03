import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import type { Visual } from "./schema";
import { colors, fontFamily, layout } from "./theme";

const pop = (frame: number, start: number, length: number) =>
  interpolate(frame, [start, start + length], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

// 항목들이 장면 앞쪽 60% 안에 순서대로 나타나도록 시작 프레임을 나눈다.
const staggerStart = (index: number, count: number, sceneFrames: number) =>
  Math.round(8 + (index * sceneFrames * 0.6) / Math.max(count, 1));

const Panel: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { width } = useVideoConfig();

  return (
    <div
      style={{
        position: "absolute",
        top: layout.visualTop,
        left: layout.side,
        width: width - layout.side * 2,
        height: layout.visualHeight,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        fontFamily,
        color: colors.text,
        wordBreak: "keep-all",
      }}
    >
      {children}
    </div>
  );
};

// "0.016%", "250배", "90% 이상" → 숫자 부분만 0부터 카운트업
const NumberVisual: React.FC<{ visual: Visual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const raw = visual.value ?? "";
  const match = raw.match(/^([^\d]*)([\d,]*\.?\d+)(.*)$/);
  const progress = pop(frame, 4, 1.2 * fps);

  let text = raw;

  if (match) {
    const [, prefix, digits, suffix] = match;
    const target = Number(digits.replace(/,/g, ""));
    const decimals = digits.includes(".") ? digits.split(".")[1].length : 0;
    const current = (target * progress).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    text = `${prefix}${current}${suffix}`;
  }

  return (
    <Panel>
      <div
        style={{
          fontSize: text.length > 7 ? 170 : 230,
          fontWeight: 900,
          letterSpacing: -6,
          color: colors.accent,
          textShadow: `0 0 60px ${colors.accentSoft}`,
          scale: String(interpolate(progress, [0, 1], [0.6, 1])),
          opacity: pop(frame, 0, 8),
        }}
      >
        {text}
      </div>
      {visual.label ? (
        <div
          style={{
            marginTop: 24,
            fontSize: 52,
            fontWeight: 700,
            color: colors.muted,
            opacity: pop(frame, 0.8 * fps, 12),
            translate: `0px ${interpolate(pop(frame, 0.8 * fps, 12), [0, 1], [30, 0])}px`,
          }}
        >
          {visual.label}
        </div>
      ) : null}
    </Panel>
  );
};

// 막대가 차례로 자라나는 비교 차트. 가장 큰 값은 강조색.
const CompareVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const bars = (visual.bars ?? []).slice(0, 4);
  const max = Math.max(...bars.map((bar) => bar.value), 1);

  return (
    <Panel>
      {visual.label ? (
        <div style={{ fontSize: 46, fontWeight: 700, color: colors.muted, marginBottom: 36 }}>
          {visual.label}
        </div>
      ) : null}
      <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 34 }}>
        {bars.map((bar, index) => {
          const grow = pop(frame, staggerStart(index, bars.length, sceneFrames), 24);
          const best = bar.value === max;

          return (
            <div key={bar.label} style={{ opacity: pop(frame, staggerStart(index, bars.length, sceneFrames), 6) }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 44, fontWeight: 700 }}>
                <span>{bar.label}</span>
                <span style={{ color: best ? colors.accent : colors.text }}>{bar.display}</span>
              </div>
              <div style={{ marginTop: 12, height: 44, borderRadius: 22, background: colors.surface }}>
                <div
                  style={{
                    height: "100%",
                    borderRadius: 22,
                    width: `${(bar.value / max) * 100 * grow}%`,
                    background: best ? colors.accent : colors.blue,
                    boxShadow: best ? `0 0 30px ${colors.accentSoft}` : "none",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

// 단계 카드가 위에서부터 하나씩 나타나고 화살표로 이어지는 흐름도
const FlowVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const items = (visual.items ?? []).slice(0, 4);

  return (
    <Panel>
      {items.map((item, index) => {
        const start = staggerStart(index, items.length, sceneFrames);
        const shown = pop(frame, start, 14);
        const last = index === items.length - 1;

        return (
          <div key={item} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                minWidth: 640,
                padding: "18px 40px",
                borderRadius: 28,
                border: `3px solid ${last ? colors.accent : colors.border}`,
                background: last ? colors.accentSoft : colors.surface,
                fontSize: 44,
                fontWeight: 700,
                textAlign: "center",
                opacity: shown,
                translate: `${interpolate(shown, [0, 1], [-80, 0])}px 0px`,
              }}
            >
              <span style={{ color: colors.accent, marginRight: 18 }}>{index + 1}</span>
              {item}
            </div>
            {last ? null : (
              <div
                style={{
                  height: 34,
                  width: 6,
                  margin: "6px 0",
                  borderRadius: 3,
                  background: colors.accent,
                  scale: `1 ${pop(frame, start + 10, 10)}`,
                  transformOrigin: "top",
                }}
              />
            )}
          </div>
        );
      })}
    </Panel>
  );
};

// 핵심 단어 카드가 튀어나오는 형태
const KeywordsVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const items = (visual.items ?? []).slice(0, 4);

  return (
    <Panel>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 28 }}>
        {items.map((item, index) => {
          const shown = pop(frame, staggerStart(index, items.length, sceneFrames), 14);

          return (
            <div
              key={item}
              style={{
                padding: "26px 44px",
                borderRadius: 999,
                background: index === 0 ? colors.accent : colors.surface,
                border: `3px solid ${index === 0 ? colors.accent : colors.border}`,
                fontSize: 54,
                fontWeight: 900,
                opacity: shown,
                scale: String(interpolate(shown, [0, 1], [0.4, 1])),
                rotate: `${interpolate(shown, [0, 1], [index % 2 ? 8 : -8, 0])}deg`,
              }}
            >
              {item}
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

// 코드가 한 글자씩 타이핑되는 터미널 창
const CodeVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const code = (visual.code ?? "").split("\n").slice(0, 7).join("\n");
  const typed = Math.round(
    interpolate(frame, [6, sceneFrames * 0.6], [0, code.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const cursorOn = Math.floor(frame / 15) % 2 === 0;

  return (
    <Panel>
      <div
        style={{
          width: "100%",
          borderRadius: 28,
          overflow: "hidden",
          border: `2px solid ${colors.border}`,
          background: "rgba(5, 7, 11, 0.85)",
          opacity: pop(frame, 0, 10),
          translate: `0px ${interpolate(pop(frame, 0, 14), [0, 1], [60, 0])}px`,
        }}
      >
        <div style={{ display: "flex", gap: 14, padding: "22px 28px", background: colors.surface }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((color) => (
            <div key={color} style={{ width: 22, height: 22, borderRadius: 11, background: color }} />
          ))}
        </div>
        <pre
          style={{
            margin: 0,
            padding: "30px 36px",
            minHeight: 360,
            fontFamily: "Consolas, 'Courier New', monospace",
            fontSize: 40,
            lineHeight: 1.45,
            color: colors.green,
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
          }}
        >
          {code.slice(0, typed)}
          <span style={{ opacity: cursorOn ? 1 : 0, color: colors.text }}>▌</span>
        </pre>
      </div>
    </Panel>
  );
};

// 엔딩 질문: 물음표가 맥박처럼 뛰고 질문이 확대된다.
const QuestionVisual: React.FC<{ visual: Visual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  const shown = pop(frame, 0, 18);

  return (
    <Panel>
      <div
        style={{
          fontSize: 300,
          fontWeight: 900,
          lineHeight: 1,
          color: colors.accent,
          scale: String(1 + Math.sin(frame / 6) * 0.05),
          opacity: shown,
        }}
      >
        ?
      </div>
      {visual.label ? (
        <div
          style={{
            marginTop: 30,
            fontSize: 62,
            fontWeight: 900,
            textAlign: "center",
            lineHeight: 1.3,
            opacity: pop(frame, 10, 16),
            scale: String(interpolate(pop(frame, 10, 16), [0, 1], [0.85, 1])),
          }}
        >
          {visual.label}
        </div>
      ) : null}
    </Panel>
  );
};

export const SceneVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  switch (visual.type) {
    case "number":
      return <NumberVisual visual={visual} />;
    case "compare":
      return <CompareVisual visual={visual} sceneFrames={sceneFrames} />;
    case "flow":
      return <FlowVisual visual={visual} sceneFrames={sceneFrames} />;
    case "keywords":
      return <KeywordsVisual visual={visual} sceneFrames={sceneFrames} />;
    case "code":
      return <CodeVisual visual={visual} sceneFrames={sceneFrames} />;
    case "question":
      return <QuestionVisual visual={visual} />;
    default:
      return null;
  }
};
