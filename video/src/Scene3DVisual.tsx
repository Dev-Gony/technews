import { useEffect, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Easing,
  interpolate,
  Loop,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { SCENE3D_LOOP_FRAMES, SCENES_3D, type Scene3D } from "./Background";
import type { Chunk, Visual } from "./schema";
import { colors, fontFamily, layout } from "./theme";
import { pop } from "./visualKit";

// 3D 장면 그림 (visual type "scene3d"): Blender로 미리 렌더링한 1080x1920 투명 루프에서
// 장면이 있는 부분(원판)만 그래픽 영역 가운데에 크게 띄운다. 자막(captionTop)은 가리지 않는다.
//
// beats(배역)가 있으면 장면이 대사를 설명하는 짧은 이야기가 된다: 처음에 장면 전체를 잠깐 보여 준 뒤,
// beat 마다 카메라가 그 사물·꼬마로 밀고 들어가고, 대상에 링과 이름표를 붙이고, 나머지는 흐리게 한다.
// 사물·꼬마의 화면 좌표는 Blender가 프레임마다 내보낸 public/assets3d/*_anchors.json 에서 읽는다.
// 이름표 파일이 없거나 beats가 없으면 예전처럼 장면 전체만 보여 준다.

// 루프 파일 안에서 장면(원판과 사물)이 차지하는 영역의 가운데와 높이 (assets3d/*_world.png 의 알파 영역 기준)
const CONTENT_CENTER_X = 505;
const CONTENT_CENTER_Y = 976;
const CONTENT_HEIGHT = 920;

const LABEL_HEIGHT = 76;
const BOTTOM_GAP = 24;

// 이야기 연출
const ESTABLISH = 8; // 처음 장면 전체를 보여 주는 프레임 (0.27초)
const MOVE = 12; // 카메라가 다음 대상으로 옮겨 가는 프레임
const MIN_BEAT = 32; // beat 하나가 머무는 최소 프레임 (이름표가 0.7초 이상 읽히게)
const TARGET_RADIUS = 170; // 밀고 들어간 뒤 대상이 화면에서 차지할 반지름(px)
const MAX_ZOOM = 2.05;
const MIN_ZOOM = 1.2;
const DIM = 0.72; // 대상 밖을 얼마나 흐리게 할지 (0 = 그대로, 1 = 안 보임)
// 확대한 장면을 잘라 보여 줄 영역 (위: 상단 제목 아래, 아래: 자막 위). 가장자리는 부드럽게 사라진다.
const CLIP_TOP = 440;
const CLIP_BOTTOM = layout.captionTop - 14;
const CLIP_FADE = 80;

type Track = [number, number, number][];
type AnchorFile = { frames: number; anchors: Record<string, { kind: string; desc: string; track: Track }> };

const anchorFile = (scene: Scene3D) => SCENES_3D[scene].replace("_loop.webm", "_anchors.json");

// 이름표 파일은 있을 때만 쓴다 (없으면 null → beats 없이 예전처럼)
const useAnchors = (scene: Scene3D | undefined, wanted: boolean): AnchorFile | null => {
  const [data, setData] = useState<AnchorFile | null>(null);
  const [handle] = useState(() => (scene && wanted ? delayRender(`3D anchors ${scene}`) : null));

  useEffect(() => {
    if (!scene || handle === null) {
      return;
    }
    fetch(staticFile(anchorFile(scene)))
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        setData(json);
        continueRender(handle);
      })
      .catch((err) => {
        // 파일이 없거나 깨졌으면 beats 없이 그린다 (매일 업로드를 멈추지 않는다)
        console.warn("3D anchors", scene, err);
        continueRender(handle);
      });
  }, [scene, handle]);

  return data;
};

// 한글 2글자 이상 겹치면 이 자막 덩어리가 beat 이름표를 말하는 순간으로 본다.
const pairs = (text: string) => {
  const clean = text.replace(/[^0-9A-Za-z가-힣]/g, "").toLowerCase();
  const out = new Set<string>();
  for (let i = 0; i + 1 < clean.length; i++) {
    out.add(clean.slice(i, i + 2));
  }
  return out;
};

// beat 시작 프레임: 그 이름표를 말하는 자막이 나오는 순간에 맞추고, 못 찾으면 컷을 고르게 나눈다.
// 어느 beat 든 MIN_BEAT 이상 머물게 한다.
export const beatStarts = (labels: string[], chunks: Chunk[], length: number): number[] => {
  const n = labels.length;
  const span = Math.max(length - ESTABLISH, 1);
  const starts: number[] = [];
  let used = -1;

  labels.forEach((label, i) => {
    const earliest = i === 0 ? ESTABLISH : starts[i - 1] + MIN_BEAT;
    const latest = length - MIN_BEAT * (n - i);
    const even = ESTABLISH + (span * i) / n;
    const want = pairs(label);
    const hit = chunks.findIndex((chunk, k) => k > used && [...pairs(chunk.text)].some((p) => want.has(p)));
    let start = even;
    if (hit >= 0) {
      // 말하기 조금 전에 카메라가 움직이기 시작해야 말하는 순간 대상에 도착한다
      start = chunks[hit].from - 6;
      used = hit;
    }
    starts.push(Math.round(Math.min(Math.max(start, earliest), Math.max(latest, earliest))));
  });

  return starts;
};

// 컷 길이에 들어가는 만큼만 beat 를 쓴다
export const fitBeats = <T,>(beats: T[], length: number) =>
  beats.slice(0, Math.max(0, Math.min(4, Math.floor((length - ESTABLISH) / MIN_BEAT))));

const ease = Easing.bezier(0.65, 0, 0.35, 1);

// 대략적인 글자 폭 (가운데 정렬 이름표를 화면 밖으로 안 나가게 맞출 때만 쓴다)
const textWidth = (text: string, size: number) =>
  [...text].reduce((sum, ch) => sum + (/[가-힣]/.test(ch) ? size : /\s/.test(ch) ? size * 0.3 : size * 0.58), 0);

export const Scene3DVisual: React.FC<{ visual: Visual; sceneFrames?: number; chunks?: Chunk[] }> = ({
  visual,
  sceneFrames = 120,
  chunks = [],
}) => {
  const frame = useCurrentFrame();
  const scene = visual.scene as Scene3D | undefined;
  const valid = Boolean(scene && scene in SCENES_3D);
  const wanted = valid && (visual.beats?.length ?? 0) > 0;
  const anchors = useAnchors(valid ? scene : undefined, wanted);

  if (!scene || !valid) {
    return null;
  }

  const beats = fitBeats(
    (visual.beats ?? []).filter((beat) => anchors?.anchors[beat.target]),
    sceneFrames,
  );
  const story = beats.length > 0 && anchors !== null;

  const label = story ? "" : (visual.label || "").trim();
  const top = layout.visualTop + (label ? LABEL_HEIGHT : 0);
  const bottom = layout.captionTop - BOTTOM_GAP;
  const s0 = (bottom - top) / CONTENT_HEIGHT;
  const centerY = (top + bottom) / 2;

  const enter = pop(frame, 0, 14);
  const labelIn = pop(frame, 6, 12);

  // ---- 카메라: 초점(f, 영상 px), 확대(z), 초점을 놓을 화면 자리(cx, cy)
  const loopIndex = ((frame % SCENE3D_LOOP_FRAMES) + SCENE3D_LOOP_FRAMES) % SCENE3D_LOOP_FRAMES;
  const point = (target: string) => {
    const track = anchors!.anchors[target].track;
    const [x, y, r] = track[loopIndex % track.length];
    return { x, y, r };
  };
  const overview = { fx: CONTENT_CENTER_X, fy: CONTENT_CENTER_Y, z: 1, cx: 540, cy: centerY };
  const starts = story ? beatStarts(beats.map((beat) => beat.label), chunks, sceneFrames) : [];
  const shot = (k: number) => {
    if (k < 0) {
      return overview;
    }
    const p = point(beats[k].target);
    const z = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, TARGET_RADIUS / Math.max(p.r * s0, 1)));
    // 대상은 영역 가운데보다 조금 아래에 두어 위에 이름표 자리를 남긴다
    return { fx: p.x, fy: p.y, z, cx: 540, cy: centerY + 50 };
  };

  // 지금 beat (시작 전이면 -1)
  let current = -1;
  starts.forEach((start, k) => {
    if (frame >= start) {
      current = k;
    }
  });
  const move = current < 0 ? 1 : interpolate(frame, [starts[current], starts[current] + MOVE], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const from = shot(current - 1);
  const to = shot(current);
  const mix = (a: number, b: number) => a + (b - a) * move;
  const cam = {
    fx: mix(from.fx, to.fx),
    fy: mix(from.fy, to.fy),
    z: mix(from.z, to.z),
    cx: mix(from.cx, to.cx),
    cy: mix(from.cy, to.cy),
  };
  const s = s0 * cam.z;
  const toScreen = (x: number, y: number) => ({ x: cam.cx + (x - cam.fx) * s, y: cam.cy + (y - cam.fy) * s });

  // ---- 지금 대상 (링·이름표·조명)
  const focus = story && current >= 0 ? point(beats[current].target) : null;
  const focusScreen = focus ? toScreen(focus.x, focus.y) : null;
  const ringR = focus ? Math.max(focus.r * s * 0.82, 46) : 0;
  const beatEnd = current >= 0 && current + 1 < starts.length ? starts[current + 1] : sceneFrames + 100;
  // 다음 beat 로 넘어가기 직전에 이름표를 거둬, 한 번에 하나만 보이게
  const out = interpolate(frame, [beatEnd - 5, beatEnd], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tagIn = current >= 0 ? pop(frame, starts[current] + MOVE - 6, 12) * out : 0;
  const ringDraw = current >= 0 ? interpolate(frame, [starts[current] + MOVE - 8, starts[current] + MOVE + 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.33, 1, 0.68, 1),
  }) : 0;
  // 흐리기는 첫 beat 에 들어가며 켜지고 끝까지 유지 (구멍만 대상에서 대상으로 옮겨 간다)
  const dim = story ? DIM * interpolate(frame, [starts[0], starts[0] + MOVE], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const hole = focusScreen ?? { x: 540, y: centerY };
  const holeR = focus ? ringR * 1.15 : 400;

  const sceneStyle = {
    position: "absolute" as const,
    left: cam.cx - cam.fx * s,
    top: cam.cy - cam.fy * s,
    width: 1080,
    height: 1920,
    transformOrigin: "0 0",
    transform: `scale(${s * interpolate(enter, [0, 1], [0.92, 1])})`,
    opacity: enter,
  };

  const video = (
    <Loop durationInFrames={SCENE3D_LOOP_FRAMES} name={`3D ${scene}`}>
      <OffthreadVideo src={staticFile(SCENES_3D[scene])} transparent muted style={{ width: 1080, height: 1920 }} />
    </Loop>
  );

  if (!story) {
    return (
      <AbsoluteFill>
        <div style={{ ...sceneStyle, left: 540 - CONTENT_CENTER_X * s0, top: centerY - CONTENT_CENTER_Y * s0, transform: `scale(${s0 * interpolate(enter, [0, 1], [0.92, 1])})` }}>
          {video}
        </div>
        {label ? <TopLabel text={label} progress={labelIn} /> : null}
      </AbsoluteFill>
    );
  }

  // 이름표 자리: 대상 위 (모자라면 아래). 화면 양옆을 넘지 않게.
  const text = current >= 0 ? beats[current].label : "";
  const fontSize = 52;
  const pillW = textWidth(text, fontSize) + 64;
  const pillH = fontSize + 32;
  const gap = 26;
  let pillTop = hole.y - ringR - gap - pillH;
  let above = true;
  if (pillTop < CLIP_TOP + 8) {
    pillTop = hole.y + ringR + gap;
    above = false;
  }
  const pillCenter = Math.min(Math.max(hole.x, pillW / 2 + 48), 1080 - pillW / 2 - 48);
  const lineFrom = { x: hole.x, y: above ? hole.y - ringR : hole.y + ringR };
  const lineTo = { x: pillCenter, y: above ? pillTop + pillH : pillTop };

  const fadeMask = `linear-gradient(to bottom, transparent 0px, black ${CLIP_FADE}px, black calc(100% - ${CLIP_FADE}px), transparent 100%)`;
  const spot = `radial-gradient(circle at ${hole.x}px ${hole.y - CLIP_TOP}px, black ${holeR}px, rgba(0,0,0,${1 - dim}) ${holeR * 1.45}px)`;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: CLIP_TOP,
          width: 1080,
          height: CLIP_BOTTOM - CLIP_TOP,
          overflow: "hidden",
          maskImage: fadeMask,
          WebkitMaskImage: fadeMask,
        }}
      >
        <div style={{ position: "absolute", inset: 0, maskImage: spot, WebkitMaskImage: spot }}>
          <div style={{ ...sceneStyle, top: sceneStyle.top - CLIP_TOP }}>{video}</div>
        </div>
      </div>

      {focusScreen && tagIn > 0.001 ? (
        <>
          <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
            <circle
              cx={hole.x}
              cy={hole.y}
              r={ringR}
              fill="none"
              stroke={colors.accent}
              strokeWidth={6}
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={1 - ringDraw}
              transform={`rotate(-90 ${hole.x} ${hole.y})`}
              opacity={out}
            />
            <line
              x1={lineFrom.x}
              y1={lineFrom.y}
              x2={lineFrom.x + (lineTo.x - lineFrom.x) * tagIn}
              y2={lineFrom.y + (lineTo.y - lineFrom.y) * tagIn}
              stroke={colors.accent}
              strokeWidth={4}
              strokeLinecap="round"
              opacity={tagIn}
            />
          </svg>
          <div
            style={{
              position: "absolute",
              left: pillCenter,
              top: pillTop,
              height: pillH,
              transform: `translate(-50%, ${interpolate(tagIn, [0, 1], [above ? 10 : -10, 0])}px) scale(${interpolate(tagIn, [0, 1], [0.9, 1])})`,
              opacity: tagIn,
              display: "flex",
              alignItems: "center",
              padding: "0 32px",
              borderRadius: 999,
              backgroundColor: colors.accent,
              color: "#FFFFFF",
              fontFamily,
              fontWeight: 900,
              fontSize,
              lineHeight: 1,
              whiteSpace: "nowrap",
            }}
          >
            {text}
          </div>
        </>
      ) : null}
    </AbsoluteFill>
  );
};

const TopLabel: React.FC<{ text: string; progress: number }> = ({ text, progress }) => (
  <div
    style={{
      position: "absolute",
      top: layout.visualTop,
      left: 0,
      width: 1080,
      display: "flex",
      justifyContent: "center",
      opacity: progress,
      transform: `translateY(${interpolate(progress, [0, 1], [12, 0])}px)`,
    }}
  >
    <div
      style={{
        fontFamily,
        fontWeight: 800,
        fontSize: 44,
        lineHeight: 1,
        padding: "14px 30px",
        borderRadius: 999,
        color: colors.text,
        border: `3px solid ${colors.accent}`,
        wordBreak: "keep-all",
      }}
    >
      {text}
    </div>
  </div>
);
