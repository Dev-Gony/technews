import { Easing, interpolate, useVideoConfig } from "remotion";
import { colors, fontFamily, layout } from "./theme";

// 그래픽 컴포넌트들이 같이 쓰는 도구: 등장 곡선, 순서대로 나타나기, 그래픽 영역(Panel)

export const pop = (frame: number, start: number, length: number) =>
  interpolate(frame, [start, start + length], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

// 항목들이 컷 앞쪽 절반 안에 빠르게 순서대로 나타나도록 시작 프레임을 나눈다.
export const staggerStart = (index: number, count: number, sceneFrames: number) =>
  Math.round((index * sceneFrames * 0.45) / Math.max(count, 1));

export const Panel: React.FC<{ children: React.ReactNode }> = ({ children }) => {
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

