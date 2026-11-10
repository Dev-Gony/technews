import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Easing,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background, is3DBackdrop, Scene3DLayer } from "./Background";
import { Captions } from "./Captions";
import type { Cut, ShortProps } from "./schema";
import { colors, fontFamily, layout, serifFamily, themeVars } from "./theme";
import { SceneVisual } from "./Visuals";

export const calculateShortMetadata: CalculateMetadataFunction<ShortProps> = ({ props }) => {
  return { durationInFrames: props.durationInFrames };
};

// 장면 전환: 다음 그래픽이 들어오는 동안 이전 그래픽은 EXIT_FRAMES 동안 살짝 작아지며 흐려진다.
// (뚝 끊기고 빈 화면이 생기지 않게 두 그래픽이 잠깐 겹친다)
export const EXIT_FRAMES = 8;

// 컷 끝까지 카메라가 밀고 들어가는 정도. 숫자·인용은 그 글자로 더 세게, 표·흐름처럼 읽을 게 많은 건 약하게.
const CAMERA_PUSH: Partial<Record<Cut["visual"]["type"], number>> = {
  number: 1.1,
  quote: 1.07,
  scene3d: 1.06,
  question: 1.06,
  compare: 1.03,
  flow: 1.03,
  diagram: 1.02,
  code: 1.02,
};

const VisualLayer: React.FC<{ cut: Cut; index: number }> = ({ cut, index }) => {
  const frame = useCurrentFrame();
  const length = Math.max(cut.durationInFrames, 8);
  const exit = interpolate(frame, [length, length + EXIT_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.4, 0, 1, 1),
  });
  const enter = interpolate(frame, [0, 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // 카메라는 멈추지 않는다: 컷 내내 천천히 밀고 들어가고(숫자는 숫자로 더 세게), 컷마다 방향을 바꿔 옆으로 흐른다.
  const push = CAMERA_PUSH[cut.visual.type] ?? 1.045;
  const side = index % 2 === 0 ? 1 : -1;
  const drift = interpolate(frame, [0, length], [side * 18, -side * 18], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        opacity: enter * (1 - exit),
        // 그래픽 영역(470~1070) 가운데를 기준으로 밀고 들어간다
        transformOrigin: "50% 40%",
        translate: `${drift}px 0px`,
        scale: String(
          interpolate(frame, [0, 7, length], [index === 0 ? 1.18 : 1.06, 1, push], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: [Easing.bezier(0.16, 1, 0.3, 1), Easing.bezier(0.33, 0, 0.67, 1)],
          }) * interpolate(exit, [0, 1], [1, 0.94]),
        ),
      }}
    >
      {index === 0 ? null : <SceneVisual visual={cut.visual} sceneFrames={cut.durationInFrames} chunks={cut.chunks} />}
    </AbsoluteFill>
  );
};

// 자막 + 첫 컷 흰 섬광 (컷 길이 그대로)
const CutView: React.FC<{ cut: Cut; index: number; pill: boolean }> = ({ cut, index, pill }) => {
  const frame = useCurrentFrame();
  const strong = index === 0;
  // 그래픽 없는 컷은 자막을 화면 가운데에 크게. 단, 첫 컷은 가운데에 제목(훅)이 있으므로 아래 자리.
  // 3D 배경(pill)일 때는 가운데를 장면에 비워 두고 자막은 늘 책상 아래 어두운 바탕 위에.
  const center = !pill && index > 0 && cut.visual.type === "none";

  return (
    <AbsoluteFill>
      <Captions chunks={cut.chunks} center={center} pill={pill} />
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

// 마무리: 화면이 차분히 어두워지며 채널 로고(it.)와 한 줄 소개가 뜬다. 쇼츠가 처음으로 돌아가기 전 "끝"을 알려준다.
const Outro: React.FC<{ channel: string }> = ({ channel }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cover = interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const logo = spring({ frame: frame - 4, fps, config: { damping: 12, stiffness: 140 } });
  const dot = spring({ frame: frame - 12, fps, config: { damping: 8, stiffness: 220 } });
  const line = interpolate(frame, [14, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, opacity: cover, alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          fontFamily: serifFamily,
          fontWeight: 900,
          fontSize: 240,
          lineHeight: 1,
          letterSpacing: -4,
          color: colors.text,
          opacity: interpolate(logo, [0, 0.4], [0, 1], { extrapolateRight: "clamp" }),
          scale: String(interpolate(logo, [0, 1], [0.85, 1])),
          marginTop: -120,
        }}
      >
        IT
        <span style={{ color: colors.accent, display: "inline-block", scale: String(dot) }}>.</span>
      </div>
      <div style={{ marginTop: 24, fontFamily, fontWeight: 900, fontSize: 46, letterSpacing: 6, color: colors.text, opacity: line }}>
        {channel}
      </div>
      <div
        style={{
          marginTop: 18,
          fontFamily,
          fontWeight: 700,
          fontSize: 36,
          color: colors.muted,
          opacity: line,
          translate: `0px ${interpolate(line, [0, 1], [16, 0])}px`,
        }}
      >
        AI·개발 뉴스, 출근·점심·퇴근길에
      </div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<ShortProps> = ({ channel, theme, cover, source, audio, cuts, sfx, outroFrom, durationInFrames, backdrop }) => {
  return (
    <AbsoluteFill style={themeVars(theme ?? "ink")}>
      <Background cuts={cuts} backdrop={backdrop ?? "glow"} />
      {is3DBackdrop(backdrop) ? <Scene3DLayer cuts={cuts} scene={backdrop} /> : null}
      <Audio src={staticFile(audio)} />
      {sfx.map((effect, index) => (
        <Audio key={`sfx-${index}`} name={effect.src} from={effect.from} src={staticFile(effect.src)} volume={effect.volume} />
      ))}
      {cuts.map((cut, index) => (
        <Sequence
          key={`visual-${index}`}
          name={`Visual ${index + 1}`}
          from={cut.from}
          durationInFrames={cut.durationInFrames + (index < cuts.length - 1 ? EXIT_FRAMES : 0)}
        >
          <VisualLayer cut={cut} index={index} />
        </Sequence>
      ))}
      {cuts.map((cut, index) => (
        <Sequence key={`cut-${index}`} name={`Cut ${index + 1}`} from={cut.from} durationInFrames={cut.durationInFrames}>
          <CutView cut={cut} index={index} pill={is3DBackdrop(backdrop)} />
        </Sequence>
      ))}
      <Cover text={cover} heroFrames={cuts[0]?.durationInFrames ?? 45} />
      <Chrome channel={channel} source={source} />
      {outroFrom !== undefined && outroFrom < durationInFrames ? (
        <Sequence name="Outro" from={outroFrom} durationInFrames={durationInFrames - outroFrom}>
          <Outro channel={channel} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
