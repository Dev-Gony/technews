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
  // 그래픽 없는 컷은 자막을 화면 가운데에 크게. 단, 첫 컷은 가운데에 제목(훅)이 있으므로 아래 자리.
  const center = index > 0 && cut.visual.type === "none";

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
        }}
      >
        {index === 0 ? null : <SceneVisual visual={cut.visual} sceneFrames={cut.durationInFrames} />}
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

// 제목(cover) = 이 영상의 훅. 첫 컷 동안은 화면 한가운데 크게 쾅 찍히고,
// 첫 컷이 끝날 때 상단으로 줄어들어 영상 내내 고정된다. 숫자가 든 어절은 골드.
export const goldDigits = (line: string) =>
  line.split(/(\s+)/).map((word, index) =>
    /\d/.test(word) ? (
      <span key={index} style={{ color: colors.gold }}>
        {word}
      </span>
    ) : (
      word
    ),
  );

const Cover: React.FC<{ text: string; heroFrames: number }> = ({ text, heroFrames }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const lines = text.split("\n").slice(0, 2);
  const longest = Math.max(...lines.map((line) => line.length), 1);
  // 0 = 화면 가운데 크게(훅), 1 = 상단 고정 제목
  const shrink = interpolate(frame, [heroFrames - 10, heroFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });
  const slam = interpolate(frame, [0, 6], [1.35, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.2, 0.9, 0.3, 1),
  });
  const heroSize = longest > 9 ? 112 : 132;
  const headerSize = longest > 10 ? 58 : 66;

  return (
    <div
      style={{
        position: "absolute",
        top: interpolate(shrink, [0, 1], [560, layout.coverTop]),
        left: layout.side / 2,
        width: width - layout.side,
        textAlign: "center",
        fontFamily: serifFamily,
        fontWeight: 900,
        fontSize: interpolate(shrink, [0, 1], [heroSize, headerSize]),
        lineHeight: 1.2,
        letterSpacing: -1.5,
        scale: String(shrink > 0 ? 1 : slam),
        wordBreak: "keep-all",
      }}
    >
      {lines.map((line, index) => (
        <div key={index} style={{ color: colors.text }}>
          {goldDigits(line)}
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
      <Cover text={cover} heroFrames={cuts[0]?.durationInFrames ?? 45} />
      <Chrome channel={channel} source={source} />
    </AbsoluteFill>
  );
};
