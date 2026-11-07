import { AbsoluteFill } from "remotion";
import { z } from "zod";
import { Background } from "./Background";
import { visualSchema } from "./schema";
import { goldDigits } from "./Short";
import { colors, fontFamily, serifFamily, themeVars } from "./theme";
import { SceneVisual } from "./Visuals";

// 쇼츠 썸네일 (1080x1920). 홈 쇼츠 선반·검색·구독 피드·채널 탭에 보인다.
// 3초 테스트 기준: 제목(훅) 하나가 가장 먼저 보이고, 아래에 그 내용을 보여주는 그림 하나.
// 피드에서 가운데가 잘려 보일 수 있어서 핵심은 화면 가운데(위아래 420~1500)에 모은다.

export const thumbnailSchema = z.object({
  channel: z.string(),
  theme: z.enum(["ink", "paper"]).optional(),
  cover: z.string(),
  // null이면 제목만. (빼면 Remotion이 defaultProps의 예시 그림을 대신 넣는다)
  visual: visualSchema.nullable().optional(),
});

export type ThumbnailProps = z.infer<typeof thumbnailSchema>;

// 그림이 다 그려진 뒤의 모습을 쓴다: shorts.py가 THUMBNAIL_FRAME 프레임을 스틸로 뽑는다
// (숫자 카운트업, 건물 내려앉기가 끝난 시점).
export const THUMBNAIL_FRAME = 90;

export const Thumbnail: React.FC<ThumbnailProps> = ({ channel, theme, cover, visual }) => {
  // 예전 영상은 긴 제목을 여러 줄로 쓴다(최대 4줄). 3줄 이상이면 그림 없이 제목만 크게.
  const lines = cover.split("\n").slice(0, 4);
  // 글자 폭 어림: 영문·숫자·공백 0.6, 한글·기호(↓ 등) 1
  const lineWidth = (line: string) => [...line].reduce((sum, ch) => sum + (/[\x20-\x7e]/.test(ch) ? 0.6 : 1), 0);
  const longest = Math.max(...lines.map(lineWidth), 1);
  const showVisual = Boolean(visual) && lines.length <= 2 && !["none", "hook", "question", "code"].includes(visual!.type);
  // 한 줄이 화면 너비(약 1000px)를 넘지 않게 글자 크기를 줄인다.
  const fontSize = Math.min(longest > 8 ? 136 : 158, Math.floor(1000 / (longest * 0.95)));

  return (
    <AbsoluteFill style={themeVars(theme ?? "ink")}>
      <Background />

      <div
        style={{
          position: "absolute",
          top: 300,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily,
          fontWeight: 900,
          fontSize: 36,
          letterSpacing: 4,
          color: colors.muted,
        }}
      >
        {channel}
      </div>

      <div
        style={{
          position: "absolute",
          top: showVisual ? 400 : 960 - (lines.length * fontSize * 1.18) / 2,
          left: 40,
          right: 40,
          textAlign: "center",
          fontFamily: serifFamily,
          fontWeight: 900,
          fontSize,
          lineHeight: 1.18,
          letterSpacing: -3,
          color: colors.text,
          wordBreak: "keep-all",
        }}
      >
        {lines.map((line, index) => (
          <div key={index}>{goldDigits(line)}</div>
        ))}
      </div>

      {showVisual ? (
        // 영상 속 그래픽 영역(470~1070)을 제목 아래로 내려서 그대로 쓴다.
        <AbsoluteFill style={{ translate: "0px 360px" }}>
          <SceneVisual visual={visual!} sceneFrames={120} />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
