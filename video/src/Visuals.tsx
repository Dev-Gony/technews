import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Visual } from "./schema";
import { colors, fontFamily, layout } from "./theme";

const pop = (frame: number, start: number, length: number) =>
  interpolate(frame, [start, start + length], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

// 항목들이 컷 앞쪽 절반 안에 빠르게 순서대로 나타나도록 시작 프레임을 나눈다.
const staggerStart = (index: number, count: number, sceneFrames: number) =>
  Math.round(3 + (index * sceneFrames * 0.45) / Math.max(count, 1));

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
          const grow = pop(frame, staggerStart(index, bars.length, sceneFrames), 14);
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
        const shown = pop(frame, start, 9);
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
          const shown = pop(frame, staggerStart(index, items.length, sceneFrames), 9);

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

// 공간·역할 비유: 층마다 떨어져 쌓이는 아이소메트릭 건물. 맨 위층(대장)은 네온 레드,
// 아래층(일꾼)은 먹색 + 골드 창문. 층 사이로 일감(점)이 오르내리고, 오른쪽에 "비유 = 실제 기술".
const isoPoints = (points: [number, number][]) => points.map(([x, y]) => `${x},${y}`).join(" ");

const MetaphorVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rooms = (visual.rooms ?? []).filter((room) => room.place.trim()).slice(0, 3);
  const count = rooms.length;
  const w = count >= 3 ? 128 : 170;
  const t = Math.round(w * 0.36);
  const gap = count >= 3 ? 26 : 44;
  const extent = w + t;
  const titleHeight = visual.label ? 78 : 0;
  const stackHeight = count * extent + (count - 1) * gap;
  const svgWidth = 2 * w + 40;
  const cx = svgWidth / 2;

  const floorTop = (index: number) => index * (extent + gap);
  const startOf = (index: number) => staggerStart(index, count, sceneFrames);
  const landed = startOf(count - 1) + 12;

  return (
    <Panel>
      {visual.label ? (
        <div
          style={{
            height: titleHeight - 18,
            marginBottom: 18,
            padding: "0 30px",
            display: "flex",
            alignItems: "center",
            borderRadius: 999,
            border: `3px solid ${colors.gold}`,
            background: colors.goldSoft,
            color: colors.gold,
            fontSize: 40,
            fontWeight: 900,
            opacity: pop(frame, 0, 8),
          }}
        >
          {visual.label}
        </div>
      ) : null}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 34, width: "100%" }}>
        <svg width={svgWidth} height={stackHeight} style={{ flexShrink: 0, overflow: "visible" }}>
          {/* 층 사이 연결선과 오르내리는 일감 */}
          {rooms.slice(0, -1).map((_, index) => {
            const y1 = floorTop(index) + extent;
            const y2 = floorTop(index + 1);
            const cycle = ((frame - landed + index * 9) % 24) / 24;
            const visible = frame >= landed;

            return (
              <g key={`link-${index}`} opacity={pop(frame, startOf(index + 1) + 6, 8)}>
                <line x1={cx} y1={y1} x2={cx} y2={y2 + w / 2} style={{ stroke: colors.gold }} strokeWidth={5} strokeDasharray="8 8" />
                {visible ? (
                  <circle
                    cx={cx}
                    cy={interpolate(cycle, [0, 1], [y1, y2 + w / 2])}
                    r={11}
                    style={{ fill: colors.gold, filter: `drop-shadow(0 0 10px ${colors.gold})` }}
                  />
                ) : null}
              </g>
            );
          })}

          {rooms.map((room, index) => {
            const drop = spring({ frame: frame - startOf(index), fps, config: { damping: 11, stiffness: 140 } });
            const top = floorTop(index);
            const cy = top + w / 2;
            const boss = index === 0;
            const face = boss
              ? { top: colors.neonRed, left: "#B3243A", right: "#7A1626", edge: "#FF8A9B" }
              : { top: colors.floorTop, left: colors.floorLeft, right: colors.floorRight, edge: colors.gold };
            const leftEdge = (a: number): [number, number] => [cx - w + a * w, cy + (a * w) / 2];
            const rightEdge = (a: number): [number, number] => [cx + a * w, cy + w / 2 - (a * w) / 2];
            const windows = [0.12, 0.42, 0.72];

            return (
              <g
                key={room.place}
                opacity={interpolate(drop, [0, 0.3], [0, 1], { extrapolateRight: "clamp" })}
                transform={`translate(0 ${interpolate(drop, [0, 1], [-170, 0])})`}
              >
                <polygon
                  points={isoPoints([[cx - w, cy], [cx, cy + w / 2], [cx, cy + w / 2 + t], [cx - w, cy + t]])}
                  style={{ fill: face.left }}
                />
                <polygon
                  points={isoPoints([[cx, cy + w / 2], [cx + w, cy], [cx + w, cy + t], [cx, cy + w / 2 + t]])}
                  style={{ fill: face.right }}
                />
                <polygon
                  points={isoPoints([[cx, cy - w / 2], [cx + w, cy], [cx, cy + w / 2], [cx - w, cy]])}
                  strokeWidth={3}
                  style={{
                    fill: face.top,
                    stroke: face.edge,
                    filter: boss ? `drop-shadow(0 0 22px ${colors.neonRed})` : undefined,
                  }}
                />
                {/* 창문: 층이 내려앉은 뒤 하나씩 불이 켜진다 */}
                {windows.map((a, windowIndex) => {
                  const lit = frame >= startOf(index) + 10 + windowIndex * 4;
                  const color = lit ? (boss ? "#FFD2D9" : colors.gold) : "rgba(255,255,255,0.12)";
                  const [lx1, ly1] = leftEdge(a);
                  const [lx2, ly2] = leftEdge(a + 0.18);
                  const [rx1, ry1] = rightEdge(a);
                  const [rx2, ry2] = rightEdge(a + 0.18);

                  return (
                    <g key={a}>
                      <polygon
                        points={isoPoints([[lx1, ly1 + t * 0.28], [lx2, ly2 + t * 0.28], [lx2, ly2 + t * 0.72], [lx1, ly1 + t * 0.72]])}
                        style={{ fill: color }}
                      />
                      <polygon
                        points={isoPoints([[rx1, ry1 + t * 0.28], [rx2, ry2 + t * 0.28], [rx2, ry2 + t * 0.72], [rx1, ry1 + t * 0.72]])}
                        style={{ fill: color }}
                        opacity={0.75}
                      />
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>

        <div style={{ position: "relative", flex: 1, height: stackHeight }}>
          {rooms.map((room, index) => {
            const shown = pop(frame, startOf(index) + 4, 10);

            return (
              <div
                key={room.place}
                style={{
                  position: "absolute",
                  top: floorTop(index) + extent / 2 - 70,
                  left: 0,
                  right: 0,
                  opacity: shown,
                  translate: `${interpolate(shown, [0, 1], [60, 0])}px 0px`,
                }}
              >
                <div style={{ fontSize: 60, fontWeight: 900, lineHeight: 1.15, color: index === 0 ? colors.neonRed : colors.text }}>
                  {room.place}
                </div>
                <div style={{ marginTop: 6, fontSize: 42, fontWeight: 700, lineHeight: 1.2, color: colors.gold }}>
                  = {room.actual}
                </div>
              </div>
            );
          })}
        </div>
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
          fontSize: text.length > 5 ? 190 : 250,
          fontWeight: 900,
          lineHeight: 1.05,
          letterSpacing: -8,
          textAlign: "center",
          color: colors.accent,
          textShadow: `0 0 80px ${colors.accentSoft}`,
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

export const SceneVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  switch (visual.type) {
    case "hook":
      return <HookVisual visual={visual} />;
    case "metaphor":
      return <MetaphorVisual visual={visual} sceneFrames={sceneFrames} />;
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
