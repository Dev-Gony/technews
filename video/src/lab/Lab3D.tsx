import {
  AbsoluteFill,
  Composition,
  interpolate,
  Loop,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "../Background";
import { colors, fontFamily, layout, serifFamily, themeVars } from "../theme";

// 3D 장면 시안 미리보기 (매일 렌더링되는 Short 와 무관한 별도 진입점: src/lab/index.ts)
// npx remotion studio src/lab/index.ts  /  npx remotion render src/lab/index.ts DeskShort out.mp4

type Chunk = { text: string; from: number; durationInFrames: number; emphasis: boolean };

const DESK_CUT = {
  from: 0,
  durationInFrames: 120,
  visual: { type: "none" as const },
  chunks: [
    { text: "주석만 지웠는데", from: 0, durationInFrames: 55, emphasis: false },
    { text: "토큰 77% 절감", from: 55, durationInFrames: 65, emphasis: true },
  ] as Chunk[],
};

// 장면 위에서도 읽히도록 어두운 바탕을 깐 자막 (책상판 아래 자리)
const PillCaption: React.FC<{ chunks: Chunk[] }> = ({ chunks }) => {
  const frame = useCurrentFrame();
  const chunk = chunks.find((c) => frame >= c.from && frame < c.from + c.durationInFrames) ?? chunks[0];
  const local = frame - chunk.from;

  return (
    <div style={{ position: "absolute", top: 1520, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div
        style={{
          padding: "18px 40px",
          borderRadius: 24,
          background: "rgba(17,17,15,0.86)",
          fontFamily,
          fontWeight: 900,
          fontSize: 76,
          letterSpacing: -2,
          color: chunk.emphasis ? "#FFC24B" : "#F7F4EA",
          scale: String(interpolate(local, [0, 4, 7], [0.8, 1.04, 1], { extrapolateRight: "clamp" })),
        }}
      >
        {chunk.text}
      </div>
    </div>
  );
};

// 숫자 칩: 토큰 탑 위에 톡 튀어나온다
const TokenChip: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - 58, fps, config: { damping: 10, stiffness: 180 } });

  return (
    <div
      style={{
        position: "absolute",
        top: 760,
        left: 40,
        padding: "14px 26px",
        borderRadius: 999,
        background: "#11110F",
        color: "#FFC24B",
        fontFamily,
        fontWeight: 900,
        fontSize: 54,
        letterSpacing: -1,
        boxShadow: "0 12px 30px rgba(17,17,15,0.25)",
        opacity: interpolate(pop, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }),
        scale: String(pop),
        rotate: "-6deg",
      }}
    >
      토큰 −77%
    </div>
  );
};

// '책상 위 꼬마 에이전트들' 장면을 쇼츠 화면 전체에 깐 예시 (paper 테마)
const DeskShort: React.FC = () => (
  <AbsoluteFill style={{ ...themeVars("paper") }}>
    <Background cuts={[DESK_CUT]} backdrop="glow" />
    <AbsoluteFill
      style={{
        backgroundImage:
          "radial-gradient(rgba(17,17,15,0.10) 3px, transparent 3.5px)",
        backgroundSize: "54px 54px",
      }}
    />
    <Loop durationInFrames={120}>
      <OffthreadVideo src={staticFile("assets3d/desk_world_loop.webm")} transparent muted style={{ width: 1080, height: 1920 }} />
    </Loop>
    <div
      style={{
        position: "absolute",
        top: 150,
        left: layout.side,
        right: layout.side,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        fontFamily,
        color: colors.muted,
      }}
    >
      <span style={{ fontSize: 32, fontWeight: 900, letterSpacing: 2 }}>itgony</span>
      <span style={{ fontSize: 26, fontWeight: 500, color: colors.faint }}>출처: GeekNews · news.hada.io</span>
    </div>
    <div
      style={{
        position: "absolute",
        top: layout.coverTop,
        left: layout.side / 2,
        right: layout.side / 2,
        textAlign: "center",
        fontFamily: serifFamily,
        fontWeight: 900,
        fontSize: 66,
        lineHeight: 1.2,
        letterSpacing: -1.5,
        color: colors.text,
      }}
    >
      코드 에이전트 토큰 <span style={{ color: colors.gold }}>77%</span> 절감
    </div>
    <TokenChip />
    <PillCaption chunks={DESK_CUT.chunks} />
  </AbsoluteFill>
);

export const LabRoot: React.FC = () => (
  <>
    <Composition id="DeskShort" component={DeskShort} durationInFrames={120} fps={30} width={1080} height={1920} />
  </>
);
