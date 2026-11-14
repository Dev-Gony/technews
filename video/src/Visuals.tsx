import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Chunk, Visual } from "./schema";
import { IsoIcon, IsoPlate, isoProject } from "./Isometric";
import { fitFontSize, Panel, pop, staggerStart } from "./visualKit";
import { IdeCodeVisual, isEditorial, useShortStyle } from "./editorial/Editorial";
import { Scene3DVisual } from "./Scene3DVisual";
import { BeforeAfterVisual, DiagramVisual, QuoteVisual, ScaleVisual } from "./VisualsPro";
import { colors, fontFamily, layout } from "./theme";

// "0.016%", "250배", "90% 이상" → 숫자 부분만 0부터 카운트업
const NumberVisual: React.FC<{ visual: Visual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const raw = visual.value ?? "";
  const match = raw.match(/^([^\d]*)([\d,]*\.?\d+)(.*)$/);
  const progress = pop(frame, 2, 0.7 * fps);

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
          fontSize: fitFontSize(raw, 230),
          whiteSpace: "nowrap",
          fontWeight: 900,
          letterSpacing: -6,
          color: colors.gold,
          fontVariantNumeric: "tabular-nums",
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
          const grow = pop(frame, staggerStart(index, bars.length, sceneFrames), 14);
          const best = bar.value === max;

          return (
            <div key={bar.label} style={{ opacity: pop(frame, staggerStart(index, bars.length, sceneFrames), 6) }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 44, fontWeight: 700 }}>
                <span>{bar.label}</span>
                <span style={{ color: best ? colors.gold : colors.muted, fontVariantNumeric: "tabular-nums" }}>{bar.display}</span>
              </div>
              <div style={{ marginTop: 12, height: 44, borderRadius: 22, background: colors.surface }}>
                <div
                  style={{
                    height: "100%",
                    borderRadius: 22,
                    width: `${(bar.value / max) * 100 * grow}%`,
                    background: best ? colors.gold : colors.blue,
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
        const shown = pop(frame, start, 9);
        const last = index === items.length - 1;

        return (
          <div key={item} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                minWidth: 640,
                padding: "18px 40px",
                borderRadius: 28,
                border: `3px solid ${last ? colors.text : colors.border}`,
                background: colors.surface,
                fontSize: 44,
                fontWeight: 700,
                textAlign: "center",
                opacity: shown,
                translate: `${interpolate(shown, [0, 1], [-80, 0])}px 0px`,
              }}
            >
              <span style={{ color: colors.muted, marginRight: 18 }}>{index + 1}</span>
              {item}
            </div>
            {last ? null : (
              <div
                style={{
                  height: 34,
                  width: 6,
                  margin: "6px 0",
                  borderRadius: 3,
                  background: colors.border,
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
          const shown = pop(frame, staggerStart(index, items.length, sceneFrames), 9);

          return (
            <div
              key={item}
              style={{
                padding: "26px 44px",
                borderRadius: 999,
                background: colors.surface,
                border: `3px solid ${index === 0 ? colors.text : colors.border}`,
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
    interpolate(frame, [3, sceneFrames * 0.7], [0, code.length], {
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
            // 고정폭 글꼴에는 한글이 없어서(서버에서 □로 보임) 한글은 본문 글꼴로 대체한다.
            fontFamily: `Consolas, 'DejaVu Sans Mono', monospace, ${fontFamily}`,
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
          fontSize: 260,
          fontWeight: 900,
          lineHeight: 1,
          color: colors.faint,
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
            fontSize: 66,
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

// 공간·역할 비유: 바닥 판 위에 사물(서버, GPU, 사람, 트럭…)을 올린 아이소메트릭 디오라마.
// 2~3개를 가로로 나란히 놓고, 사이로 일감(점)이 오가며, 각 사물 아래에 "비유 = 실제 기술".
// 첫 번째(핵심)만 브랜드 빨강, 나머지는 종이·먹색.
const MetaphorVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const rooms = (visual.rooms ?? []).filter((room) => room.place.trim()).slice(0, 3);
  const count = rooms.length;
  const titleHeight = visual.label ? 60 : 0;
  const labelHeight = 130;
  const gap = 24;
  const areaWidth = width - layout.side * 2 + 40;
  const colWidth = (areaWidth - gap * (count - 1)) / count;
  // 그림 크기: 칸 너비와 남은 높이 중 작은 쪽에 맞춘다.
  const u = Math.min(colWidth / (2 * 0.866 * 1.2), (layout.visualHeight + 30 - titleHeight - labelHeight) / 2.45, 175);
  const artHeight = u * 2.45;
  // 아이콘 바닥 가운데가 놓이는 높이
  const baseY = u * 1.45;
  const colCenter = (index: number) => index * (colWidth + gap) + colWidth / 2;
  const startOf = (index: number) => staggerStart(index, count, sceneFrames);
  const landed = startOf(count - 1) + 12;
  const [ox, oy] = isoProject(u, 0.5, 0.5, 0);

  return (
    <Panel>
      {visual.label ? (
        <div
          style={{
            height: titleHeight - 14,
            marginBottom: 14,
            color: colors.muted,
            fontSize: 34,
            fontWeight: 900,
            letterSpacing: 2,
            opacity: pop(frame, 0, 8),
          }}
        >
          {visual.label}
        </div>
      ) : null}
      <div style={{ position: "relative", width: areaWidth, height: artHeight + labelHeight }}>
        <svg width={areaWidth} height={artHeight} style={{ position: "absolute", top: 0, left: 0, overflow: "visible" }}>
          {/* 칸 사이 연결선과 오가는 일감 */}
          {rooms.slice(0, -1).map((_, index) => {
            const x1 = colCenter(index) + u * 0.95;
            const x2 = colCenter(index + 1) - u * 0.95;
            const y = baseY - u * 0.1;
            const cycle = ((frame - landed + index * 9) % 26) / 26;

            return (
              <g key={`link-${index}`} opacity={pop(frame, startOf(index + 1) + 6, 8)}>
                <line x1={x1} y1={y} x2={x2} y2={y} style={{ stroke: colors.border }} strokeWidth={4} strokeDasharray="8 8" />
                {frame >= landed ? <circle cx={interpolate(cycle, [0, 1], [x1, x2])} cy={y} r={9} style={{ fill: colors.gold }} /> : null}
              </g>
            );
          })}

          {rooms.map((room, index) => {
            const drop = spring({ frame: frame - startOf(index), fps, config: { damping: 12, stiffness: 150 } });
            const iconPop = spring({ frame: frame - startOf(index) - 5, fps, config: { damping: 10, stiffness: 180 } });
            const main = index === 0;

            return (
              <g
                key={room.place}
                opacity={interpolate(drop, [0, 0.3], [0, 1], { extrapolateRight: "clamp" })}
                transform={`translate(${colCenter(index) - ox} ${baseY - oy + interpolate(drop, [0, 1], [-140, 0])})`}
              >
                <IsoPlate u={u} main={main} />
                <g transform={`translate(${ox} ${oy}) scale(${interpolate(iconPop, [0, 1], [0.4, 1])}) translate(${-ox} ${-oy})`}>
                  <IsoIcon name={room.icon ?? "building"} u={u} main={main} />
                </g>
              </g>
            );
          })}
        </svg>

        {rooms.map((room, index) => {
          const shown = pop(frame, startOf(index) + 6, 10);

          return (
            <div
              key={room.place}
              style={{
                position: "absolute",
                top: artHeight,
                left: colCenter(index) - colWidth / 2,
                width: colWidth,
                textAlign: "center",
                opacity: shown,
                translate: `0px ${interpolate(shown, [0, 1], [24, 0])}px`,
              }}
            >
              <div style={{ fontSize: count >= 3 ? 46 : 56, fontWeight: 900, lineHeight: 1.15, color: index === 0 ? colors.accent : colors.text }}>
                {room.place}
              </div>
              <div style={{ marginTop: 6, fontSize: count >= 3 ? 30 : 36, fontWeight: 700, lineHeight: 1.25, color: colors.muted }}>
                {room.actual}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

// 첫 컷: 화면을 꽉 채운 문구가 쾅 하고 내려찍힌다.
const HookVisual: React.FC<{ visual: Visual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  const text = visual.value ?? "";
  const slam = interpolate(frame, [0, 5], [2.4, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.5, 0, 0.9, 0.6),
  });
  // 내려찍은 직후 짧게 흔들린다.
  const shake = frame >= 5 && frame < 14 ? Math.sin(frame * 2.7) * (14 - frame) * 2.2 : 0;

  return (
    <Panel>
      <div
        style={{
          fontSize: fitFontSize(text, 250),
          fontWeight: 900,
          lineHeight: 1.05,
          letterSpacing: -8,
          textAlign: "center",
          color: colors.accent,
          scale: String(slam),
          translate: `${shake}px ${-shake / 2}px`,
          opacity: interpolate(frame, [0, 2], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        {text}
      </div>
    </Panel>
  );
};

export const SceneVisual: React.FC<{ visual: Visual; sceneFrames: number; chunks?: Chunk[] }> = ({ visual, sceneFrames, chunks }) => {
  const style = useShortStyle();

  // news/explain 스타일의 코드는 문법 색·강조 줄이 있는 에디터 창으로
  if (visual.type === "code" && isEditorial(style)) {
    return <IdeCodeVisual visual={visual} sceneFrames={sceneFrames} />;
  }

  switch (visual.type) {
    case "hook":
      return <HookVisual visual={visual} />;
    case "metaphor":
      return <MetaphorVisual visual={visual} sceneFrames={sceneFrames} />;
    case "diagram":
      return <DiagramVisual visual={visual} sceneFrames={sceneFrames} />;
    case "beforeafter":
      return <BeforeAfterVisual visual={visual} sceneFrames={sceneFrames} />;
    case "scale":
      return <ScaleVisual visual={visual} sceneFrames={sceneFrames} />;
    case "scene3d":
      return <Scene3DVisual visual={visual} sceneFrames={sceneFrames} chunks={chunks} />;
    case "quote":
      return <QuoteVisual visual={visual} sceneFrames={sceneFrames} />;
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
