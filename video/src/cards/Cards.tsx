import { loadFont as loadSerif } from "@remotion/google-fonts/NotoSerifKR";
import type { CalculateMetadataFunction } from "remotion";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily as sans } from "../theme";
import type { CardsProps, Slide } from "./schema";

// 인스타그램 카드뉴스. GONY DAILY 웹 신문과 같은 종이색·먹색·명조 제목.
// 프레임 하나 = 카드 한 장 (fps 1, 길이 = 장 수).

const { fontFamily: serif } = loadSerif("normal", {
  weights: ["700", "900"],
  subsets: ["korean", "latin"],
});

const paper = {
  bg: "#F7F4EA",
  deep: "#EEE9DC",
  ink: "#11110F",
  muted: "#625F58",
  hairline: "rgba(17, 17, 15, 0.34)",
  soft: "rgba(17, 17, 15, 0.14)",
  red: "#D4382C",
};

const SIDE = 84;

export const calculateCardsMetadata: CalculateMetadataFunction<CardsProps> = ({ props }) => {
  return { durationInFrames: Math.max(props.slides.length, 1) };
};

const Label: React.FC<{ text?: string }> = ({ text }) =>
  text ? (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        fontFamily: sans,
        fontWeight: 900,
        fontSize: 30,
        letterSpacing: 2,
        color: paper.red,
        marginBottom: 34,
      }}
    >
      <div style={{ width: 18, height: 18, background: paper.red }} />
      {text}
    </div>
  ) : null;

const Title: React.FC<{ text?: string; size?: number }> = ({ text, size = 66 }) =>
  text ? (
    <div
      style={{
        fontFamily: serif,
        fontWeight: 900,
        fontSize: size,
        lineHeight: 1.28,
        letterSpacing: -1.5,
        color: paper.ink,
        wordBreak: "keep-all",
        whiteSpace: "pre-line",
      }}
    >
      <Marked text={text} />
    </div>
  ) : null;

// **강조** 표시한 부분만 빨간색으로
const Marked: React.FC<{ text: string }> = ({ text }) => (
  <>
    {text.split("**").map((part, index) =>
      index % 2 === 1 ? (
        <span key={index} style={{ color: paper.red }}>
          {part}
        </span>
      ) : (
        part
      ),
    )}
  </>
);

const Body: React.FC<{ text?: string; size?: number }> = ({ text, size = 38 }) =>
  text ? (
    <div
      style={{
        marginTop: 34,
        fontFamily: sans,
        fontWeight: 500,
        fontSize: size,
        lineHeight: 1.6,
        color: paper.muted,
        wordBreak: "keep-all",
        whiteSpace: "pre-line",
      }}
    >
      {text}
    </div>
  ) : null;

const Cover: React.FC<{ slide: Slide; section: string }> = ({ slide, section }) => (
  <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: "100%" }}>
    <Label text={slide.label || section} />
    <Title text={slide.title} size={(slide.title ?? "").length > 22 ? 92 : 108} />
    <div style={{ width: 120, height: 10, background: paper.red, margin: "44px 0 0" }} />
    <Body text={slide.body} size={40} />
  </div>
);

const Story: React.FC<{ slide: Slide }> = ({ slide }) => (
  <div>
    <Label text={slide.label} />
    <Title text={slide.title} />
    <div style={{ marginTop: 44 }}>
      {(slide.items ?? []).slice(0, 4).map((item, index) => (
        <div
          key={item}
          style={{
            display: "flex",
            gap: 30,
            padding: "30px 0",
            borderTop: `2px solid ${paper.soft}`,
          }}
        >
          <div style={{ fontFamily: serif, fontWeight: 900, fontSize: 48, color: paper.red, minWidth: 64, lineHeight: 1.2 }}>
            {String(index + 1).padStart(2, "0")}
          </div>
          <div style={{ fontFamily: sans, fontWeight: 700, fontSize: 38, lineHeight: 1.5, color: paper.ink, wordBreak: "keep-all" }}>
            {item}
          </div>
        </div>
      ))}
    </div>
  </div>
);

const NumberSlide: React.FC<{ slide: Slide }> = ({ slide }) => {
  const value = slide.value ?? "";

  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: "100%", textAlign: "center" }}>
      <Label text={slide.label} />
      <div
        style={{
          fontFamily: serif,
          fontWeight: 900,
          // 길이에 맞춰 한 줄에 들어가게 줄인다 ("1/10" → 크게, "B200 56대" → 작게)
          fontSize: value.length <= 4 ? 290 : value.length <= 6 ? 220 : 160,
          lineHeight: 1,
          letterSpacing: value.length <= 6 ? -8 : -4,
          whiteSpace: "nowrap",
          color: paper.red,
          margin: "10px 0 40px",
        }}
      >
        {value}
      </div>
      <Title text={slide.title} size={58} />
      <Body text={slide.body} size={36} />
    </div>
  );
};

const Flow: React.FC<{ slide: Slide }> = ({ slide }) => {
  const steps = (slide.items ?? []).slice(0, 4);

  return (
    <div>
      <Label text={slide.label} />
      <Title text={slide.title} size={60} />
      <div style={{ marginTop: 50 }}>
        {steps.map((step, index) => {
          const last = index === steps.length - 1;

          return (
            <div key={step}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 28,
                  padding: "28px 34px",
                  border: `3px solid ${paper.ink}`,
                  background: last ? paper.ink : "transparent",
                  color: last ? paper.bg : paper.ink,
                }}
              >
                <div style={{ fontFamily: serif, fontWeight: 900, fontSize: 44, color: last ? paper.bg : paper.red }}>
                  {index + 1}
                </div>
                <div style={{ fontFamily: sans, fontWeight: 700, fontSize: 38, lineHeight: 1.4, wordBreak: "keep-all" }}>
                  {step}
                </div>
              </div>
              {last ? null : <div style={{ width: 3, height: 34, background: paper.ink, marginLeft: 56 }} />}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Checklist: React.FC<{ slide: Slide }> = ({ slide }) => (
  <div>
    <Label text={slide.label} />
    <Title text={slide.title} size={60} />
    <div style={{ marginTop: 48, display: "flex", flexDirection: "column", gap: 26 }}>
      {(slide.items ?? []).slice(0, 4).map((item) => (
        <div
          key={item}
          style={{
            display: "flex",
            gap: 28,
            alignItems: "flex-start",
            padding: "30px 32px",
            background: paper.deep,
          }}
        >
          <div
            style={{
              flexShrink: 0,
              width: 40,
              height: 40,
              marginTop: 6,
              border: `4px solid ${paper.ink}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: sans,
              fontWeight: 900,
              fontSize: 30,
              color: paper.red,
            }}
          >
            ✓
          </div>
          <div style={{ fontFamily: sans, fontWeight: 700, fontSize: 38, lineHeight: 1.5, color: paper.ink, wordBreak: "keep-all" }}>
            {item}
          </div>
        </div>
      ))}
    </div>
  </div>
);

const Caution: React.FC<{ slide: Slide }> = ({ slide }) => (
  <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: "100%" }}>
    <Label text={slide.label} />
    <Title text={slide.title} size={62} />
    <div
      style={{
        marginTop: 48,
        padding: "40px 44px",
        borderLeft: `14px solid ${paper.red}`,
        background: paper.deep,
        fontFamily: serif,
        fontWeight: 700,
        fontSize: 44,
        lineHeight: 1.55,
        color: paper.ink,
        wordBreak: "keep-all",
      }}
    >
      {slide.body}
    </div>
  </div>
);

const Outro: React.FC<{ slide: Slide; handle: string }> = ({ slide, handle }) => (
  <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: "100%", textAlign: "center" }}>
    <Label text={slide.label} />
    <Title text={slide.title} size={84} />
    <Body text={slide.body} size={36} />
    <div style={{ display: "flex", justifyContent: "center", gap: 18, marginTop: 70 }}>
      {["저장", "공유", `팔로우 ${handle}`].map((text, index) => (
        <div
          key={text}
          style={{
            padding: "20px 34px",
            border: `3px solid ${paper.ink}`,
            background: index === 2 ? paper.ink : "transparent",
            color: index === 2 ? paper.bg : paper.ink,
            fontFamily: sans,
            fontWeight: 900,
            fontSize: 32,
          }}
        >
          {text}
        </div>
      ))}
    </div>
  </div>
);

const SlideBody: React.FC<{ slide: Slide; props: CardsProps }> = ({ slide, props }) => {
  switch (slide.type) {
    case "cover":
      return <Cover slide={slide} section={props.section} />;
    case "story":
      return <Story slide={slide} />;
    case "number":
      return <NumberSlide slide={slide} />;
    case "flow":
      return <Flow slide={slide} />;
    case "checklist":
      return <Checklist slide={slide} />;
    case "caution":
      return <Caution slide={slide} />;
    case "outro":
      return <Outro slide={slide} handle={props.handle} />;
    default:
      return null;
  }
};

export const Cards: React.FC<CardsProps> = (props) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const index = Math.min(frame, props.slides.length - 1);
  const slide = props.slides[index];
  const isCover = slide.type === "cover";

  return (
    <AbsoluteFill style={{ backgroundColor: paper.bg }}>
      {/* 신문 머리 */}
      <div style={{ position: "absolute", top: 60, left: SIDE, width: width - SIDE * 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontFamily: serif, fontWeight: 900, fontSize: 38, letterSpacing: 3, color: paper.ink }}>
            {props.masthead}
          </div>
          <div style={{ fontFamily: sans, fontWeight: 700, fontSize: 26, color: paper.muted }}>
            {props.date} · {props.section}
          </div>
        </div>
        <div style={{ marginTop: 18, borderTop: `4px solid ${paper.ink}` }} />
        <div style={{ marginTop: 6, borderTop: `1px solid ${paper.ink}` }} />
      </div>

      {/* 본문 */}
      <div style={{ position: "absolute", top: 190, left: SIDE, width: width - SIDE * 2, height: height - 190 - 170 }}>
        <SlideBody slide={slide} props={props} />
      </div>

      {/* 아래 줄 */}
      <div style={{ position: "absolute", bottom: 64, left: SIDE, width: width - SIDE * 2 }}>
        <div style={{ borderTop: `1px solid ${paper.hairline}`, marginBottom: 22 }} />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontFamily: sans,
            fontWeight: 700,
            fontSize: 26,
            color: paper.muted,
          }}
        >
          <span>{isCover ? props.source : props.handle}</span>
          <span style={{ color: isCover ? paper.red : paper.muted }}>
            {isCover ? "넘겨서 보기 →" : `${index + 1} / ${props.slides.length}`}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
