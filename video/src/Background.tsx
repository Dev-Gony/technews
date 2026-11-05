import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { colors } from "./theme";

// 배경: 고정된 신문 지면 가로줄(종이색 테마만) + 가장자리 비네트 + 천천히 떠다니는 붉은 빛
export const Background: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(0deg, ${colors.rule} 0px, ${colors.rule} 2px, transparent 2px, transparent 72px)`,
        }}
      />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, transparent 55%, ${colors.vignette} 100%)` }} />
      <div
        style={{
          position: "absolute",
          width: 1100,
          height: 1100,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${colors.glow} 0%, transparent 65%)`,
          translate: `${interpolate(Math.sin(frame / 90), [-1, 1], [-300, 300])}px ${interpolate(
            Math.cos(frame / 120),
            [-1, 1],
            [0, 700],
          )}px`,
        }}
      />
    </AbsoluteFill>
  );
};
