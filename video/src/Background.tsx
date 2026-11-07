import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import type { Cut } from "./schema";
import { colors, serifFamily } from "./theme";

// 배경: 비네트 + 장면마다 자리를 옮기는 빛 + (선택) 장면 핵심어를 크게 깐 지면 타이포.
// 장식이 아니라 "장면이 바뀌었다"는 리듬을 주는 용도라, 아주 흐리고 천천히 움직인다.

export type Backdrop = "glow" | "type";

// 장면이 바뀔 때마다 빛이 옮겨 가는 자리 (화면 좌표, 1080x1920)
const ANCHORS: [number, number][] = [
  [-200, 300],
  [380, 900],
  [-120, 1150],
  [420, 380],
  [0, 700],
];

// 숫자 장면은 골드 빛, 문제·구조 장면은 빨간 빛, 나머지는 흐린 빨강
const GOLD_TYPES = ["number", "scale", "beforeafter", "compare"];

const sceneWord = (cut: Cut) => {
  const visual = cut.visual;
  const candidates = [
    visual.type === "beforeafter" ? visual.after?.value : undefined,
    ["number", "scale", "hook"].includes(visual.type) ? visual.value : undefined,
    cut.chunks.find((chunk) => chunk.emphasis)?.text,
  ];

  return (candidates.find((word) => word && word.replace(/\s/g, "").length <= 8) ?? "").replace(/[.,?!]+$/, "");
};

export const Background: React.FC<{ cuts?: Cut[]; backdrop?: Backdrop }> = ({ cuts = [], backdrop = "glow" }) => {
  const frame = useCurrentFrame();
  const index = Math.max(cuts.reduce((found, cut, i) => (cut.from <= frame ? i : found), -1), 0);
  const cut = cuts[index];
  const since = cut ? frame - cut.from : frame;
  const move = interpolate(since, [0, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });
  const from = ANCHORS[Math.max(index - 1, 0) % ANCHORS.length];
  const to = ANCHORS[index % ANCHORS.length];
  const drift = [Math.sin(frame / 80) * 60, Math.cos(frame / 110) * 80];
  const x = interpolate(move, [0, 1], [from[0], to[0]]) + drift[0];
  const y = interpolate(move, [0, 1], [from[1], to[1]]) + drift[1];

  const isGold = (i: number) => Boolean(cuts[i] && GOLD_TYPES.includes(cuts[i].visual.type));
  const goldNow = isGold(index) ? 1 : 0;
  const goldBefore = isGold(index - 1) ? 1 : 0;
  const gold = interpolate(move, [0, 1], [goldBefore, goldNow]);

  const word = cut ? sceneWord(cut) : "";
  const wordIn = interpolate(since, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const wordOut = cut ? interpolate(frame, [cut.from + cut.durationInFrames - 8, cut.from + cut.durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  }) : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(0deg, ${colors.rule} 0px, ${colors.rule} 2px, transparent 2px, transparent 72px)`,
        }}
      />

      {/* 장면마다 자리를 옮기는 빛: 빨강과 골드를 겹쳐 두고 장면 종류에 따라 섞는다 */}
      {[
        { color: colors.glow, opacity: 1 - gold },
        { color: colors.glowGold, opacity: gold },
      ].map((layer, layerIndex) => (
        <div
          key={layerIndex}
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 1300,
            height: 1300,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${layer.color} 0%, transparent 65%)`,
            opacity: layer.opacity,
            translate: `${x - 110}px ${y - 650}px`,
          }}
        />
      ))}

      {/* 지면 타이포: 장면 핵심어를 아주 크게, 윤곽선만, 아주 흐리게. 화면 아래 빈자리를 채운다 */}
      {backdrop === "type" && word ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 1300,
            textAlign: "center",
            whiteSpace: "nowrap",
            fontFamily: serifFamily,
            fontWeight: 900,
            fontSize: Math.min(320, Math.floor(1150 / Math.max([...word].length, 1))),
            letterSpacing: -8,
            color: "transparent",
            WebkitTextStroke: `2px ${colors.text}`,
            opacity: 0.09 * wordIn * wordOut,
            translate: `${interpolate(since, [0, 120], [40, -40], { extrapolateRight: "extend" })}px 0px`,
          }}
        >
          {word}
        </div>
      ) : null}

      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, transparent 55%, ${colors.vignette} 100%)` }} />
    </AbsoluteFill>
  );
};
