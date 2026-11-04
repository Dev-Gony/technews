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
import { colors, fontFamily, layout } from "./theme";
import { SceneVisual } from "./Visuals";

export const calculateShortMetadata: CalculateMetadataFunction<ShortProps> = ({ props }) => {
  return { durationInFrames: props.durationInFrames };
};

// 컷이 바뀔 때마다 화면이 확 다가왔다가 자리 잡는다(펀치인). 숫자·훅 컷은 흰 섬광.
const CutView: React.FC<{ cut: Cut; index: number }> = ({ cut, index }) => {
  const frame = useCurrentFrame();
  const strong = index === 0 || cut.visual.type === "hook" || cut.visual.type === "number";
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
          translate: `${(index % 2 === 0 ? -1 : 1) * interpolate(frame, [0, cut.durationInFrames], [0, 14])}px 0px`,
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

// 상단 고정 제목. 두 번째 줄은 강조색.
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
        textAlign: "center",
        fontFamily,
        fontWeight: 900,
        fontSize: longest > 10 ? 66 : 78,
        lineHeight: 1.18,
        letterSpacing: -1.5,
        wordBreak: "keep-all",
      }}
    >
      {lines.map((line, index) => (
        <div key={index} style={{ color: index === lines.length - 1 && lines.length > 1 ? colors.highlight : colors.text }}>
          {line}
        </div>
      ))}
    </div>
  );
};

// 상단 채널명 + 전체 진행 막대, 하단 출처
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
          fontSize: 40,
          fontWeight: 900,
          color: colors.accent,
          letterSpacing: 1,
        }}
      >
        {channel}
      </div>
      <div
        style={{
          position: "absolute",
          top: 215,
          left: layout.side,
          width: width - layout.side * 2,
          height: 8,
          borderRadius: 4,
          background: colors.surface,
        }}
      >
        <div
          style={{
            height: "100%",
            borderRadius: 4,
            width: `${(frame / Math.max(durationInFrames - 1, 1)) * 100}%`,
            background: colors.accent,
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          top: 1530,
          left: layout.side,
          fontSize: 32,
          fontWeight: 500,
          color: colors.muted,
        }}
      >
        {source}
      </div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<ShortProps> = ({ channel, cover, source, audio, cuts, sfx }) => {
  return (
    <AbsoluteFill>
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
