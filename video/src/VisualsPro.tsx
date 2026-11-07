import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { IsoIcon, IsoThing, isoProject } from "./Isometric";
import type { Visual } from "./schema";
import { colors, layout, serifFamily } from "./theme";
import { Panel, pop } from "./visualKit";

// 애프터이펙트식 연출을 코드로: 선이 그려지는 화살표(Trim Paths), 카메라 줌인, 전후 분할, 규모 격자, 신문 인용.

const AREA_WIDTH = 1080 - layout.side * 2; // 920
const AREA_HEIGHT = layout.visualHeight; // 600

const ease = (frame: number, start: number, length: number) =>
  interpolate(frame, [start, start + length], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });

// 2차 베지어 곡선 위의 점
const bezier = (p0: [number, number], c: [number, number], p1: [number, number], t: number): [number, number] => [
  (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0],
  (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1],
];

// "약 10분의 1", "$0.30", "1,200만" → 숫자 하나 (없으면 null)
const firstNumber = (text: string) => {
  const match = text.replace(/,/g, "").match(/\d+(\.\d+)?/);

  return match ? Number(match[0]) : null;
};

// ---------------------------------------------------------------------------
// 구조도: 사물들이 차례로 놓이고, 화살표가 선을 따라 그려지고, 일감이 흐른 뒤 카메라가 핵심 마디로 밀고 들어간다.
// ---------------------------------------------------------------------------

const NODE_LAYOUTS: Record<number, [number, number][]> = {
  2: [[230, 300], [690, 300]],
  3: [[170, 380], [460, 190], [750, 380]],
  4: [[140, 390], [360, 190], [580, 390], [800, 190]],
};

export const DiagramVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nodes = (visual.nodes ?? []).filter((node) => node.label.trim()).slice(0, 4);
  const count = Math.max(nodes.length, 2);
  const points = NODE_LAYOUTS[count] ?? NODE_LAYOUTS[4];
  const u = count <= 2 ? 125 : count === 3 ? 108 : 90;
  const focus = Math.min(Math.max(visual.focus ?? count - 1, 0), nodes.length - 1);

  // 시간표: 마디 등장(앞 35%) → 화살표 그리기 → 일감 흐름 → 줌인(60%부터)
  const nodeStart = (index: number) => Math.round(2 + (index * sceneFrames * 0.35) / count);
  const linkStart = (index: number) => nodeStart(index + 1) - 2;
  const linkLength = Math.max(Math.round(sceneFrames * 0.12), 8);
  const zoomStart = Math.round(sceneFrames * 0.6);
  const zoom = ease(frame, zoomStart, Math.max(Math.round(sceneFrames * 0.22), 10));
  const [fx, fy] = points[focus] ?? points[0];

  const links = nodes.slice(0, -1).map((_, index) => {
    const [x0, y0] = points[index];
    const [x1, y1] = points[index + 1];
    // 사물 몸통을 피해 위쪽으로 휘는 곡선
    const p0: [number, number] = [x0 + u * 0.95, y0 - u * 0.55];
    const p1: [number, number] = [x1 - u * 0.95, y1 - u * 0.55];
    const c: [number, number] = [(p0[0] + p1[0]) / 2, Math.min(p0[1], p1[1]) - u * 0.9];

    return { p0, c, p1 };
  });

  return (
    <Panel>
      {/* 줌인할 때 그래픽 영역 밖(제목·자막 자리)으로 넘치지 않게 자른다 */}
      <div style={{ width: AREA_WIDTH + 80, height: AREA_HEIGHT + 40, overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          position: "relative",
          width: AREA_WIDTH,
          height: AREA_HEIGHT,
          transformOrigin: `${fx}px ${fy - u * 0.4}px`,
          scale: String(interpolate(zoom, [0, 1], [1, 1.45])),
          translate: `${interpolate(zoom, [0, 1], [0, AREA_WIDTH / 2 - fx])}px ${interpolate(zoom, [0, 1], [0, AREA_HEIGHT / 2 - fy + u * 0.2])}px`,
        }}
      >
        <svg width={AREA_WIDTH} height={AREA_HEIGHT} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          {links.map(({ p0, c, p1 }, index) => {
            const draw = ease(frame, linkStart(index), linkLength);
            const flowing = frame >= linkStart(index) + linkLength;
            const [tx, ty] = [p1[0] - c[0], p1[1] - c[1]];
            const angle = (Math.atan2(ty, tx) * 180) / Math.PI;
            const dim = interpolate(zoom, [0, 1], [1, index === focus - 1 ? 1 : 0.3]);

            return (
              <g key={`link-${index}`} opacity={dim}>
                {/* 선이 처음부터 끝까지 그려진다 (애프터이펙트 Trim Paths) */}
                <path
                  d={`M ${p0[0]} ${p0[1]} Q ${c[0]} ${c[1]} ${p1[0]} ${p1[1]}`}
                  pathLength={1}
                  strokeDasharray="1"
                  strokeDashoffset={1 - draw}
                  strokeWidth={6}
                  strokeLinecap="round"
                  style={{ fill: "none", stroke: colors.muted }}
                />
                <polygon
                  points="0,-11 20,0 0,11"
                  transform={`translate(${p1[0]} ${p1[1]}) rotate(${angle})`}
                  opacity={draw > 0.97 ? 1 : 0}
                  style={{ fill: colors.muted }}
                />
                {flowing
                  ? [0, 0.5].map((offset) => {
                      const t = ((frame - linkStart(index) - linkLength) / 22 + offset) % 1;
                      const [px, py] = bezier(p0, c, p1, t);

                      return <circle key={offset} cx={px} cy={py} r={10} style={{ fill: colors.gold }} />;
                    })
                  : null}
              </g>
            );
          })}

          {nodes.map((node, index) => {
            const appear = spring({ frame: frame - nodeStart(index), fps, config: { damping: 12, stiffness: 160 } });
            const [x, y] = points[index];
            const isFocus = index === focus;

            return (
              <g
                key={node.label}
                opacity={interpolate(appear, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }) * interpolate(zoom, [0, 1], [1, isFocus ? 1 : 0.3])}
                transform={`translate(0 ${interpolate(appear, [0, 1], [-90, 0])})`}
              >
                <IsoThing name={node.icon ?? "building"} u={u} main={isFocus} x={x} y={y} scale={interpolate(appear, [0, 1], [0.6, 1])} />
              </g>
            );
          })}
        </svg>

        {nodes.map((node, index) => {
          const [x, y] = points[index];
          const shown = pop(frame, nodeStart(index) + 5, 10);
          const isFocus = index === focus;

          return (
            <div
              key={node.label}
              style={{
                position: "absolute",
                left: x - 150,
                top: y + u * 0.75,
                width: 300,
                textAlign: "center",
                fontSize: count >= 4 ? 38 : 44,
                fontWeight: 900,
                lineHeight: 1.2,
                color: isFocus && zoom > 0.3 ? colors.accent : colors.text,
                opacity: shown * interpolate(zoom, [0, 1], [1, isFocus ? 1 : 0.3]),
              }}
            >
              {node.label}
            </div>
          );
        })}
      </div>
      </div>
    </Panel>
  );
};

// ---------------------------------------------------------------------------
// 전후 비교: 가운데 선이 위에서 아래로 그어지고, 왼쪽 "전", 오른쪽 "후"가 차례로. 숫자 크기에 따라 사물 크기도 바뀐다.
// ---------------------------------------------------------------------------

export const BeforeAfterVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const before = visual.before ?? { title: "", value: "" };
  const after = visual.after ?? { title: "", value: "" };
  const a = firstNumber(before.value);
  const b = firstNumber(after.value);
  // 큰 쪽을 1로, 작은 쪽은 크기 비율만큼 작게 (너무 작아지지 않게 0.45까지)
  const ratio = a && b ? Math.max(Math.min(Math.sqrt(b / a), 1 / 0.55), 0.55) : 1;
  const beforeScale = ratio > 1 ? 1 / ratio : 1;
  const afterScale = ratio > 1 ? 1 : ratio;
  const divider = ease(frame, 2, 12);
  const leftIn = spring({ frame: frame - 6, fps, config: { damping: 13 } });
  const rightStart = Math.round(sceneFrames * 0.32);
  const rightIn = spring({ frame: frame - rightStart, fps, config: { damping: 13 } });
  const u = 150;

  const side = (data: typeof before, appear: number, scale: number, isAfter: boolean) => (
    <div
      style={{
        width: AREA_WIDTH / 2 - 30,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        opacity: interpolate(appear, [0, 0.4], [0, 1], { extrapolateRight: "clamp" }),
        translate: `${interpolate(appear, [0, 1], [isAfter ? 80 : -80, 0])}px 0px`,
      }}
    >
      <div style={{ fontSize: 34, fontWeight: 900, letterSpacing: 2, color: isAfter ? colors.gold : colors.muted }}>
        {isAfter ? "후" : "전"}
      </div>
      <div style={{ marginTop: 6, fontSize: 42, fontWeight: 900, color: colors.text, textAlign: "center", minHeight: 56 }}>
        {data.title}
      </div>
      <svg width={400} height={330} style={{ overflow: "visible", marginTop: 6 }}>
        <IsoThing name={data.icon ?? "coins"} u={u} main={!isAfter} x={200} y={225} scale={scale} />
      </svg>
      <div
        style={{
          marginTop: 8,
          fontSize: 92,
          fontWeight: 900,
          letterSpacing: -2,
          fontVariantNumeric: "tabular-nums",
          color: isAfter ? colors.gold : colors.muted,
          textDecoration: isAfter ? "none" : "line-through",
          textDecorationThickness: 5,
          textDecorationColor: colors.accent,
          textAlign: "center",
        }}
      >
        {data.value}
      </div>
    </div>
  );

  return (
    <Panel>
      <div style={{ position: "relative", width: AREA_WIDTH, display: "flex", justifyContent: "space-between" }}>
        {side(before, leftIn, beforeScale, false)}
        <div
          style={{
            position: "absolute",
            left: AREA_WIDTH / 2 - 2,
            top: 0,
            width: 4,
            height: `${divider * 100}%`,
            background: colors.border,
          }}
        />
        {side(after, rightIn, afterScale, true)}
      </div>
    </Panel>
  );
};

// ---------------------------------------------------------------------------
// 규모: 같은 사물이 격자로 물결치듯 채워진다. "GPU 56개", "엔지니어 2,000명"을 눈으로 체감.
// ---------------------------------------------------------------------------

export const ScaleVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = Math.max(visual.count ?? 12, 1);
  const shown = Math.min(total, 60);
  const cols = shown <= 12 ? 4 : shown <= 30 ? 6 : 10;
  const rows = Math.ceil(shown / cols);
  // 아이소메트릭이라 줄 간격은 칸 너비의 0.6배면 충분하다
  const cell = Math.min(AREA_WIDTH / cols, 400 / (rows * 0.6 + 0.6));
  const u = cell * 0.62;
  const [ox, oy] = isoProject(u, 0.5, 0.5, 0);
  const fillFrames = sceneFrames * 0.45;
  const header = pop(frame, 0, 10);

  return (
    <Panel>
      <div
        style={{
          fontSize: 120,
          fontWeight: 900,
          lineHeight: 1,
          letterSpacing: -4,
          color: colors.gold,
          fontVariantNumeric: "tabular-nums",
          opacity: header,
          scale: String(interpolate(header, [0, 1], [0.8, 1])),
        }}
      >
        {visual.value}
      </div>
      <svg width={cols * cell} height={rows * cell * 0.6 + u} style={{ overflow: "visible", marginTop: 24 }}>
        {Array.from({ length: shown }, (_, index) => {
          const col = index % cols;
          const row = Math.floor(index / cols);
          // 왼쪽 위에서 오른쪽 아래로 물결치듯
          const start = 6 + ((col + row) / (cols + rows)) * fillFrames;
          const appear = spring({ frame: frame - start, fps, config: { damping: 11, stiffness: 200 } });

          return (
            <g
              key={index}
              opacity={interpolate(appear, [0, 0.3], [0, 1], { extrapolateRight: "clamp" })}
              transform={`translate(${col * cell + cell / 2 - ox} ${row * cell * 0.6 + u * 0.9 - oy + interpolate(appear, [0, 1], [-30, 0])})`}
            >
              <IsoIcon name={visual.icon ?? "person"} u={u} main={index === 0} />
            </g>
          );
        })}
      </svg>
      {visual.label ? (
        <div style={{ marginTop: 20, fontSize: 40, fontWeight: 700, color: colors.muted, opacity: pop(frame, fillFrames, 10) }}>
          {visual.label}
        </div>
      ) : null}
    </Panel>
  );
};

// ---------------------------------------------------------------------------
// 원문 인용: 신문에서 오려낸 종이 조각이 떨어지고, **핵심 구절**에 빨간 형광펜이 그어진다.
// ---------------------------------------------------------------------------

export const QuoteVisual: React.FC<{ visual: Visual; sceneFrames: number }> = ({ visual, sceneFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drop = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
  const marker = ease(frame, Math.round(sceneFrames * 0.3), Math.max(Math.round(sceneFrames * 0.25), 10));
  const parts = (visual.quote ?? "").split("**");
  const length = (visual.quote ?? "").replace(/\*\*/g, "").length;

  return (
    <Panel>
      <div
        style={{
          position: "relative",
          width: AREA_WIDTH - 40,
          padding: "56px 56px 44px",
          background: "#F2EEE3",
          color: "#11110F",
          rotate: `${interpolate(drop, [0, 1], [-5, -1.5])}deg`,
          translate: `0px ${interpolate(drop, [0, 1], [-60, 0])}px`,
          opacity: interpolate(drop, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }),
          // 그림자 대신 종이 두께처럼 보이는 단색 테두리
          boxShadow: "10px 10px 0 rgba(0, 0, 0, 0.35)",
        }}
      >
        <div style={{ position: "absolute", top: -34, left: 34, fontFamily: serifFamily, fontWeight: 900, fontSize: 150, lineHeight: 1, color: colors.accent }}>
          “
        </div>
        <div
          style={{
            fontFamily: serifFamily,
            fontWeight: 900,
            fontSize: length > 40 ? 52 : 60,
            lineHeight: 1.5,
            letterSpacing: -1,
            wordBreak: "keep-all",
          }}
        >
          {parts.map((part, index) =>
            index % 2 === 1 ? (
              <span
                key={index}
                style={{
                  backgroundImage: "linear-gradient(transparent 58%, rgba(239, 75, 60, 0.55) 58%)",
                  backgroundRepeat: "no-repeat",
                  backgroundSize: `${marker * 100}% 100%`,
                }}
              >
                {part}
              </span>
            ) : (
              part
            ),
          )}
        </div>
        {visual.label ? (
          <div style={{ marginTop: 26, fontSize: 30, fontWeight: 700, color: "#625F58", fontFamily: "inherit" }}>— {visual.label}</div>
        ) : null}
      </div>
    </Panel>
  );
};
