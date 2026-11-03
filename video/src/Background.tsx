import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { colors } from "./theme";

// 장면이 바뀌어도 계속 움직이는 배경: 천천히 떠다니는 빛 번짐 + 흐르는 점 격자
export const Background: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.09) 2px, transparent 2px)",
          backgroundSize: "48px 48px",
          backgroundPosition: `0px ${-frame * 0.6}px`,
          opacity: 0.6,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 900,
          height: 900,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${colors.accentSoft} 0%, transparent 65%)`,
          translate: `${interpolate(Math.sin(frame / 90), [-1, 1], [-260, 260])}px ${interpolate(
            Math.cos(frame / 120),
            [-1, 1],
            [-120, 380],
          )}px`,
        }}
      />
      <div
        style={{
          position: "absolute",
          right: -300,
          bottom: 200,
          width: 1000,
          height: 1000,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(77,141,255,0.16) 0%, transparent 65%)",
          translate: `${interpolate(Math.cos(frame / 100), [-1, 1], [-200, 120])}px ${interpolate(
            Math.sin(frame / 140),
            [-1, 1],
            [-300, 100],
          )}px`,
        }}
      />
    </AbsoluteFill>
  );
};
