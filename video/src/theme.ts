import type { CSSProperties } from "react";
import { loadFont } from "@remotion/google-fonts/NotoSansKR";

export const { fontFamily } = loadFont("normal", {
  weights: ["500", "700", "900"],
  subsets: ["korean", "latin"],
});

// 채널 브랜드(먹색·종이색·빨강)에 맞춘 쇼츠 배경 테마.
// ink: 프로필 사진처럼 먹색 바탕 / paper: 배너·카드뉴스처럼 종이색 바탕
export const palettes = {
  ink: {
    background: "#11110F",
    surface: "rgba(247, 244, 234, 0.08)",
    border: "rgba(247, 244, 234, 0.18)",
    text: "#F7F4EA",
    muted: "#A39E92",
    accent: "#E5483A",
    accentSoft: "rgba(229, 72, 58, 0.22)",
    highlight: "#FF5A4A",
    blue: "#8A857A",
    neonRed: "#FF3D5A",
    gold: "#FFC24B",
    goldSoft: "rgba(255, 194, 75, 0.16)",
    stroke: "#000000",
    shadow: "rgba(0, 0, 0, 0.55)",
    rule: "transparent",
    vignette: "rgba(0, 0, 0, 0.55)",
    glow: "rgba(229, 72, 58, 0.16)",
    floorTop: "#2E2D29",
    floorLeft: "#21201D",
    floorRight: "#181815",
  },
  paper: {
    background: "#F7F4EA",
    surface: "rgba(17, 17, 15, 0.06)",
    border: "rgba(17, 17, 15, 0.22)",
    text: "#11110F",
    muted: "#625F58",
    accent: "#D4382C",
    accentSoft: "rgba(212, 56, 44, 0.14)",
    highlight: "#D4382C",
    blue: "#8C877C",
    neonRed: "#E0263F",
    gold: "#B07A12",
    goldSoft: "rgba(176, 122, 18, 0.12)",
    stroke: "#F7F4EA",
    shadow: "rgba(17, 17, 15, 0.12)",
    rule: "rgba(17, 17, 15, 0.07)",
    vignette: "rgba(17, 17, 15, 0.06)",
    glow: "rgba(212, 56, 44, 0.07)",
    floorTop: "#2E2D29",
    floorLeft: "#11110F",
    floorRight: "#000000",
  },
};

export type ThemeName = keyof typeof palettes;
type ColorKey = keyof (typeof palettes)["ink"];

// 컴포넌트는 CSS 변수만 쓰고, 실제 색은 Short 맨 바깥에서 테마로 정한다.
export const colors = {
  ...(Object.fromEntries(Object.keys(palettes.ink).map((key) => [key, `var(--c-${key})`])) as Record<ColorKey, string>),
  // 코드 터미널은 테마와 상관없이 어두운 창 + 초록 글자
  green: "#3DDC97",
};

export const themeVars = (theme: ThemeName): CSSProperties =>
  Object.fromEntries(Object.entries(palettes[theme]).map(([key, value]) => [`--c-${key}`, value])) as CSSProperties;

// Shorts 화면에서 제목, 버튼에 가리지 않는 영역 (1080x1920 기준)
export const layout = {
  side: 80,
  coverTop: 250,
  visualTop: 470,
  visualHeight: 600,
  captionTop: 1110,
};
