import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Word } from "./schema";
import { colors, fontFamily, layout } from "./theme";

// 한 화면(두 줄)에 들어가는 만큼씩 끊어서 보여준다.
const PAGE_CHARS = 26;

const toPages = (words: Word[]) => {
  const pages: Word[][] = [];
  let current: Word[] = [];
  let chars = 0;

  for (const word of words) {
    if (current.length && chars + word.text.length > PAGE_CHARS) {
      pages.push(current);
      current = [];
      chars = 0;
    }

    current.push(word);
    chars += word.text.length + 1;

    // 문장이 끝나면 다음 페이지로 넘긴다.
    if (/[.?!]$/.test(word.text)) {
      pages.push(current);
      current = [];
      chars = 0;
    }
  }

  if (current.length) {
    pages.push(current);
  }

  return pages;
};

// 말하는 단어를 노래방 자막처럼 강조한다.
export const Captions: React.FC<{ words: Word[] }> = ({ words }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const ms = (frame / fps) * 1000;

  const pages = toPages(words);
  const page =
    pages.find((p) => ms < p[p.length - 1].endMs + 150) ?? pages[pages.length - 1] ?? [];

  return (
    <div
      style={{
        position: "absolute",
        top: layout.captionTop,
        left: layout.side,
        width: width - layout.side * 2,
        minHeight: 200,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignContent: "flex-start",
        gap: "8px 18px",
        fontFamily,
        fontWeight: 700,
        fontSize: 60,
        lineHeight: 1.3,
        textAlign: "center",
      }}
    >
      {page.map((word, index) => {
        const active = ms >= word.startMs && ms < word.endMs;
        const spoken = ms >= word.endMs;

        return (
          <span
            key={`${word.startMs}-${index}`}
            style={{
              color: active ? colors.accent : spoken ? colors.text : colors.dim,
              scale: active ? "1.08" : "1",
              textShadow: "0 4px 18px rgba(0,0,0,0.6)",
            }}
          >
            {word.text}
          </span>
        );
      })}
    </div>
  );
};
