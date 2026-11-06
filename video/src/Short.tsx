import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "./Background";
import { Captions } from "./Captions";
import type { Cut, ShortProps } from "./schema";
import { colors, fontFamily, layout, serifFamily, themeVars } from "./theme";
import { SceneVisual } from "./Visuals";

export const calculateShortMetadata: CalculateMetadataFunction<ShortProps> = ({ props }) => {
  return { durationInFrames: props.durationInFrames };
};

// 컷이 바뀔 때마다 화면이 살짝 다가왔다가 자리 잡는다(펀치인). 흰 섬광은 첫 컷에만.
const CutView: React.FC<{ cut: Cut; index: number }> = ({ cut, index }) => {
  const frame = useCurrentFrame();
  const strong = index === 0;
  const center = cut.visual.type === "none";

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          scale: String(
            interpolate(frame, [0, 7, cut.durationInFrames], [strong ? 1.18 : 1.1, 1, 1.03], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: [Easing.bezier(0.16, 1, 0.3, 1), Easing.linear],
            }),
          ),
          // 왼쪽 기준선이 흔들리지 않게 왼쪽 여백을 중심으로 확대한다.
          transformOrigin: `${layout.side}px 50%`,
        }}
      >
        <SceneVisual visual={cut.visual} sceneFrames={cut.durationInFrames} />
      </AbsoluteFill>
      <Captions chunks={cut.chunks} center={center} />
      {strong ? (
        <AbsoluteFill
          style={{
            backgroundColor: "#FFFFFF",
            opacity: interpolate(frame, [0, 5], [0.55, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};

// 상단 고정 제목. 브랜드 명조, 왼쪽 정렬, 한 가지 색. 이정표 역할이라 그래픽보다 작게.
const Cover: React.FC<{ text: string }> = ({ text }) => {
  const { width } = useVideoConfig();
  const lines = text.split("\n").slice(0, 2);
  const longest = Math.max(...lines.map((line) => line.length), 1);

  return (
    <div
      style={{
        position: "absolute",
        top: layout.coverTop,
        left: layout.side,
        width: width - layout.side * 2,
        textAlign: "left",
        fontFamily: serifFamily,
        fontWeight: 900,
        fontSize: longest > 10 ? 56 : 64,
        lineHeight: 1.22,
        letterSpacing: -1,
        wordBreak: "keep-all",
      }}
    >
      {lines.map((line, index) => (
        <div key={index} style={{ color: colors.text }}>
          {line}
        </div>
      ))}
    </div>
  );
};

// 상단 한 줄: 채널명(왼쪽) + 출처(오른쪽), 그 아래 얇은 진행 막대. 콘텐츠보다 눈에 덜 띄게 회색.
const Chrome: React.FC<{ channel: string; source: string }> = ({ channel, source }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width } = useVideoConfig();

  return (
    <AbsoluteFill style={{ fontFamily }}>
      <div
        style={{
          position: "absolute",
          top: 150,
          left: layout.side,
          width: width - layout.side * 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          color: colors.muted,
        }}
      >
        <span style={{ fontSize: 32, fontWeight: 900, letterSpacing: 2 }}>{channel}</span>
        <span style={{ fontSize: 26, fontWeight: 500, color: colors.faint }}>{source}</span>
      </div>
      <div
        style={{
          position: "absolute",
          top: 208,
          left: layout.side,
          width: width - layout.side * 2,
          height: 4,
          borderRadius: 2,
          background: colors.surface,
        }}
      >
        <div
          style={{
            height: "100%",
            borderRadius: 2,
            width: `${(frame / Math.max(durationInFrames - 1, 1)) * 100}%`,
            background: colors.muted,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<ShortProps> = ({ channel, theme, cover, source, audio, cuts, sfx }) => {
  return (
    <AbsoluteFill style={themeVars(theme ?? "ink")}>
      <Background />
      <Audio src={staticFile(audio)} />
      {sfx.map((effect, index) => (
        <Audio key={`sfx-${index}`} name={effect.src} from={effect.from} src={staticFile(effect.src)} volume={effect.volume} />
      ))}
      {cuts.map((cut, index) => (
        <Sequence key={`cut-${index}`} name={`Cut ${index + 1}`} from={cut.from} durationInFrames={cut.durationInFrames}>
          <CutView cut={cut} index={index} />
        </Sequence>
      ))}
      <Cover text={cover} />
      <Chrome channel={channel} source={source} />
    </AbsoluteFill>
  );
};
