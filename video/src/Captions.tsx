import { Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import type { Chunk } from "./schema";
import { colors, fontFamily, layout } from "./theme";

// 1~2어절씩 툭 튀어나오는 자막. 가운데 정렬, 발광 없음. 강조 단어는 숫자면 골드, 아니면 빨강.
const emphasisColor = (text: string) => (/\d/.test(text) ? colors.gold : colors.neonRed);

const PopWord: React.FC<{ chunk: Chunk; center: boolean }> = ({ chunk, center }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const size = center ? 132 : 100;

  return (
    <div
      style={{
        position: "absolute",
        top: center ? 760 : layout.captionTop,
        left: layout.side / 2,
        width: width - layout.side,
        textAlign: "center",
        fontFamily,
        fontWeight: 900,
        fontSize: chunk.text.length > 7 ? size * 0.82 : size,
        lineHeight: 1.15,
        letterSpacing: -2,
        wordBreak: "keep-all",
        color: chunk.emphasis ? emphasisColor(chunk.text) : colors.text,
        opacity: interpolate(frame, [0, 2], [0, 1], { extrapolateRight: "clamp" }),
        scale: String(
          interpolate(frame, [0, 4, 7], [0.7, 1.05, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.2, 0.9, 0.3, 1),
          }),
        ),
        rotate: `${interpolate(frame, [0, 6], [chunk.emphasis ? -3 : -1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })}deg`,
      }}
    >
      {chunk.text}
    </div>
  );
};

export const Captions: React.FC<{ chunks: Chunk[]; center: boolean }> = ({ chunks, center }) => {
  return (
    <>
      {chunks.map((chunk, index) => (
        <Sequence key={`${chunk.from}-${index}`} name={chunk.text} from={chunk.from} durationInFrames={chunk.durationInFrames}>
          <PopWord chunk={chunk} center={center} />
        </Sequence>
      ))}
    </>
  );
};
