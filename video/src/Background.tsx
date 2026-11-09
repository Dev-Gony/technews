import { AbsoluteFill, Easing, interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import type { Cut } from "./schema";
import { colors, serifFamily } from "./theme";

// 배경: 비네트 + 장면마다 자리를 옮기는 빛 + (선택) 장면 핵심어를 크게 깐 지면 타이포.
// 장식이 아니라 "장면이 바뀌었다"는 리듬을 주는 용도라, 아주 흐리고 천천히 움직인다.

// 3D 배경: Blender 로 미리 렌더링한 장면 (video/assets3d/). 1080x1920 VP9 알파, 360프레임(12초) 끊김 없는 루프.
// desk3d 책상 위 꼬마 에이전트들 / vault3d 살짝 열린 금고(보안) / coins3d 저울·동전·영수증(비용)
// server3d 작은 서버실(인프라·성능) / lab3d 점수판·시상대·실험대(모델 연구·벤치마크)
export const SCENES_3D = {
  desk3d: "assets3d/desk_world_loop.webm",
  vault3d: "assets3d/vault_world_loop.webm",
  coins3d: "assets3d/coins_world_loop.webm",
  server3d: "assets3d/server_world_loop.webm",
  lab3d: "assets3d/lab_world_loop.webm",
} as const;
export type Scene3D = keyof typeof SCENES_3D;
export type Backdrop = "glow" | "type" | Scene3D;

export const is3DBackdrop = (backdrop: Backdrop | undefined): backdrop is Scene3D =>
  Boolean(backdrop && backdrop in SCENES_3D);

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

// 걷는 꼬마들이 루프 동안 정확히 한 바퀴를 돈다 (모든 장면 같은 길이)
export const SCENE3D_LOOP_FRAMES = 360;

// 장면 위에 그래픽이 올라오는 동안 3D 장면을 배경색으로 얼마나 덮을지 (0 = 그대로, 1 = 완전히 가림)
// 첫 컷은 화면 가운데 큰 제목(훅)이 있어 반쯤, 그래픽 컷은 그래픽이 읽히도록 많이, 그래픽 없는 컷은 장면을 그대로 보여 준다.
const SCENE3D_HOOK_DIM = 0.55;
const SCENE3D_VISUAL_DIM = 0.82;
const SCENE3D_FADE_FRAMES = 8;

const sceneDim = (cut: Cut | undefined, index: number) => {
  if (!cut) return 0;
  if (index === 0) return SCENE3D_HOOK_DIM;
  return cut.visual.type === "none" ? 0 : SCENE3D_VISUAL_DIM;
};

// 3D 배경: 장면은 계속 돌고, 그 위 덮개만 컷에 맞춰 짙어지거나 걷힌다. (모든 3D 장면이 같은 규칙)
export const Scene3DLayer: React.FC<{ cuts?: Cut[]; scene: Scene3D }> = ({ cuts = [], scene }) => {
  const frame = useCurrentFrame();
  const index = Math.max(cuts.reduce((found, cut, i) => (cut.from <= frame ? i : found), -1), 0);
  const cut = cuts[index];
  const since = cut ? frame - cut.from : frame;
  const before = index > 0 ? sceneDim(cuts[index - 1], index - 1) : sceneDim(cut, index);
  const dim = interpolate(since, [0, SCENE3D_FADE_FRAMES], [before, sceneDim(cut, index)], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });

  return (
    <AbsoluteFill>
      <Loop durationInFrames={SCENE3D_LOOP_FRAMES} name={`3D ${scene}`}>
        <OffthreadVideo src={staticFile(SCENES_3D[scene])} transparent muted style={{ width: 1080, height: 1920 }} />
      </Loop>
      <AbsoluteFill style={{ backgroundColor: colors.background, opacity: dim }} />
    </AbsoluteFill>
  );
};
