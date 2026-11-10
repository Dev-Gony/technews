import { loadFont as loadSerif } from "@remotion/google-fonts/NotoSerifKR";
import { AbsoluteFill } from "remotion";
import { fontFamily as sans } from "../theme";

// 채널 꾸미기용 이미지 (유튜브·인스타·스레드 공통).
// 카드뉴스(종이색·먹색·명조)와 쇼츠(어두운 배경·빨간 포인트)를 한 브랜드로 묶는다.

const { fontFamily: serif } = loadSerif("normal", {
  weights: ["900"],
  subsets: ["korean", "latin"],
});

export const brand = {
  paper: "#F7F4EA",
  ink: "#11110F",
  night: "#0B0E14",
  muted: "#625F58",
  red: "#D4382C",
};

export type ProfileVariant = "paper" | "ink";

// 프로필 사진 (800x800). 유튜브·인스타 모두 원형으로 잘리므로 가운데에 모은다.
export const Profile: React.FC<{ variant: ProfileVariant }> = ({ variant }) => {
  const dark = variant === "ink";
  const fg = dark ? brand.paper : brand.ink;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: dark ? brand.ink : brand.paper,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: 380, borderTop: `10px solid ${fg}` }} />
        <div style={{ width: 380, marginTop: 8, borderTop: `3px solid ${fg}` }} />
        <div
          style={{
            fontFamily: serif,
            fontWeight: 900,
            fontSize: 270,
            lineHeight: 1,
            letterSpacing: -10,
            color: fg,
            margin: "28px 0 6px",
            display: "flex",
            alignItems: "flex-end",
          }}
        >
          it
          <span style={{ color: brand.red }}>.</span>
        </div>
        <div
          style={{
            fontFamily: sans,
            fontWeight: 900,
            fontSize: 52,
            letterSpacing: 18,
            marginLeft: 18,
            color: fg,
          }}
        >
          GONY
        </div>
        <div style={{ width: 380, marginTop: 30, borderTop: `3px solid ${fg}` }} />
      </div>
    </AbsoluteFill>
  );
};

// 유튜브 배너 (2560x1440). 모든 기기에서 보이는 영역은 가운데 1546x423뿐이다.
export const Banner: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: brand.paper }}>
      <div
        style={{
          position: "absolute",
          left: (2560 - 1546) / 2,
          top: (1440 - 423) / 2,
          width: 1546,
          height: 423,
          backgroundColor: brand.paper,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 70px",
          boxSizing: "border-box",
        }}
      >
        <div>
          <div style={{ width: 640, borderTop: `8px solid ${brand.ink}` }} />
          <div style={{ width: 640, marginTop: 6, borderTop: `2px solid ${brand.ink}` }} />
          <div
            style={{
              fontFamily: serif,
              fontWeight: 900,
              fontSize: 150,
              lineHeight: 1.05,
              letterSpacing: -4,
              color: brand.ink,
              margin: "10px 0 34px",
            }}
          >
            itgony<span style={{ color: brand.red }}>.</span>
          </div>
          <div style={{ width: 640, borderTop: `2px solid ${brand.ink}` }} />
          <div
            style={{
              fontFamily: sans,
              fontWeight: 700,
              fontSize: 30,
              letterSpacing: 4,
              color: brand.muted,
              marginTop: 16,
            }}
          >
            THE DAILY TECH BRIEFING
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontFamily: serif,
              fontWeight: 900,
              fontSize: 76,
              lineHeight: 1.3,
              letterSpacing: -2,
              color: brand.ink,
            }}
          >
            오늘 꼭 알아야 할
            <br />
            <span style={{ color: brand.red }}>테크 뉴스</span>, 1분 요약
          </div>
          <div
            style={{
              display: "inline-block",
              marginTop: 26,
              padding: "14px 26px",
              backgroundColor: brand.ink,
              color: brand.paper,
              fontFamily: sans,
              fontWeight: 900,
              fontSize: 30,
              letterSpacing: 1,
            }}
          >
            매일 6편 · 출근·점심·퇴근길
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// 영상 워터마크(구독 버튼, 150x150). 영상 위에 작게 뜨므로 단순하게.
export const Watermark: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: brand.ink,
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "50%",
      }}
    >
      <div
        style={{
          fontFamily: serif,
          fontWeight: 900,
          fontSize: 92,
          lineHeight: 1,
          letterSpacing: -4,
          color: brand.paper,
          marginTop: -8,
        }}
      >
        it<span style={{ color: brand.red }}>.</span>
      </div>
    </AbsoluteFill>
  );
};
