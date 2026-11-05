import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { colors } from "./theme";

// 장면이 바뀌어도 계속 움직이는 배경: 신문 지면처럼 흐르는 가로줄 + 천천히 떠다니는 붉은 빛
export const Background: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(0deg, ${colors.rule} 0px, ${colors.rule} 2px, transparent 2px, transparent 72px)`,
          backgroundPosition: `0px ${-frame * 0.5}px`,
        }}
      />
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
