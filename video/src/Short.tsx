import { Audio } from "@remotion/media";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "./Background";
import { Captions } from "./Captions";
import { type Scene, type ShortProps, TRANSITION_FRAMES } from "./schema";
import { colors, fontFamily, layout } from "./theme";
import { SceneVisual } from "./Visuals";

export const calculateShortMetadata: CalculateMetadataFunction<ShortProps> = ({ props }) => {
  const total = props.scenes.reduce((sum, scene) => sum + scene.durationInFrames, 0);
  const overlaps = Math.max(props.scenes.length - 1, 0) * TRANSITION_FRAMES;

  return { durationInFrames: Math.max(total - overlaps, 1) };
};

const Headline: React.FC<{ text: string; big: boolean }> = ({ text, big }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const shown = interpolate(frame, [0, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        position: "absolute",
        top: big ? 560 : layout.headlineTop,
        left: layout.side,
        width: width - layout.side * 2,
        textAlign: "center",
        fontFamily,
      }}
    >
      <div
        style={{
          fontSize: big ? 130 : 96,
          fontWeight: 900,
          lineHeight: 1.15,
          letterSpacing: -2,
          color: colors.text,
          opacity: shown,
          translate: `0px ${interpolate(shown, [0, 1], [40, 0])}px`,
        }}
      >
        {text}
      </div>
      <div
        style={{
          margin: "26px auto 0",
          width: 140,
          height: 12,
          borderRadius: 6,
          background: colors.accent,
          scale: `${interpolate(frame, [8, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} 1`,
        }}
      />
    </div>
  );
};

const SceneView: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        // 장면 내내 아주 천천히 다가오는 카메라
        scale: String(interpolate(frame, [0, scene.durationInFrames], [1, 1.04])),
      }}
    >
      <Audio src={staticFile(scene.audio)} />
      <Headline text={scene.headline} big={scene.visual.type === "none"} />
      <SceneVisual visual={scene.visual} sceneFrames={scene.durationInFrames} />
      <Captions words={scene.words} />
    </AbsoluteFill>
  );
};

// 상단 채널명 + 전체 진행 막대, 하단 출처. 장면 전환과 상관없이 고정.
const Chrome: React.FC<{ channel: string; source: string }> = ({ channel, source }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width } = useVideoConfig();

  return (
    <AbsoluteFill style={{ fontFamily }}>
      <div
        style={{
          position: "absolute",
          top: 130,
          left: layout.side,
          fontSize: 44,
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
          top: 200,
          left: layout.side,
          width: width - layout.side * 2,
          height: 10,
          borderRadius: 5,
          background: colors.surface,
        }}
      >
        <div
          style={{
            height: "100%",
            borderRadius: 5,
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
          fontSize: 34,
          fontWeight: 500,
          color: colors.muted,
        }}
      >
        {source}
      </div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<ShortProps> = ({ channel, source, scenes }) => {
  return (
    <AbsoluteFill>
      <Background />
      <TransitionSeries>
        {scenes.flatMap((scene, index) => {
          const items = [
            <TransitionSeries.Sequence key={`scene-${index}`} name={`Scene ${index + 1}`} durationInFrames={scene.durationInFrames}>
              <SceneView scene={scene} />
            </TransitionSeries.Sequence>,
          ];

          if (index < scenes.length - 1) {
            items.push(
              <TransitionSeries.Transition
                key={`transition-${index}`}
                presentation={index % 2 === 0 ? slide({ direction: "from-right" }) : fade()}
                timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
              />,
            );
          }

          return items;
        })}
      </TransitionSeries>
      <Chrome channel={channel} source={source} />
    </AbsoluteFill>
  );
};
