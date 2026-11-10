import { AbsoluteFill, interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { SCENE3D_LOOP_FRAMES, SCENES_3D, type Scene3D } from "./Background";
import type { Visual } from "./schema";
import { colors, fontFamily, layout } from "./theme";
import { pop } from "./visualKit";

// 3D 장면 그림 (visual type "scene3d"): Blender로 미리 렌더링한 1080x1920 투명 루프에서
// 장면이 있는 부분(원판)만 그래픽 영역 가운데에 크게 띄운다. 자막(captionTop)은 가리지 않는다.

// 루프 파일 안에서 장면(원판과 사물)이 차지하는 영역의 가운데와 높이 (assets3d/*_world.png 의 알파 영역 기준)
const CONTENT_CENTER_X = 505;
const CONTENT_CENTER_Y = 976;
const CONTENT_HEIGHT = 920;

const LABEL_HEIGHT = 76;
const BOTTOM_GAP = 24;

export const Scene3DVisual: React.FC<{ visual: Visual }> = ({ visual }) => {
  const frame = useCurrentFrame();
  const scene = visual.scene as Scene3D | undefined;

  if (!scene || !(scene in SCENES_3D)) {
    return null;
  }

  const label = (visual.label || "").trim();
  const top = layout.visualTop + (label ? LABEL_HEIGHT : 0);
  const bottom = layout.captionTop - BOTTOM_GAP;
  const scale = (bottom - top) / CONTENT_HEIGHT;
  const centerY = (top + bottom) / 2;

  const enter = pop(frame, 0, 14);
  const labelIn = pop(frame, 6, 12);

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 540 - CONTENT_CENTER_X * scale,
          top: centerY - CONTENT_CENTER_Y * scale,
          width: 1080,
          height: 1920,
          transformOrigin: "0 0",
          transform: `scale(${scale * interpolate(enter, [0, 1], [0.92, 1])})`,
          opacity: enter,
        }}
      >
        <Loop durationInFrames={SCENE3D_LOOP_FRAMES} name={`3D ${scene}`}>
          <OffthreadVideo src={staticFile(SCENES_3D[scene])} transparent muted style={{ width: 1080, height: 1920 }} />
        </Loop>
      </div>

      {label ? (
        <div
          style={{
            position: "absolute",
            top: layout.visualTop,
            left: 0,
            width: 1080,
            display: "flex",
            justifyContent: "center",
            opacity: labelIn,
            transform: `translateY(${interpolate(labelIn, [0, 1], [12, 0])}px)`,
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
            {label}
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
