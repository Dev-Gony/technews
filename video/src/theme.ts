import { loadFont } from "@remotion/google-fonts/NotoSansKR";

export const { fontFamily } = loadFont("normal", {
  weights: ["500", "700", "900"],
  subsets: ["korean", "latin"],
});

export const colors = {
  background: "#0B0E14",
  surface: "rgba(255, 255, 255, 0.06)",
  border: "rgba(255, 255, 255, 0.12)",
  text: "#F5F6F8",
  muted: "#8C94A0",
  dim: "rgba(245, 246, 248, 0.38)",
  accent: "#FF5C4D",
  accentSoft: "rgba(255, 92, 77, 0.18)",
  blue: "#4D8DFF",
  green: "#3DDC97",
};

// Shorts 화면에서 제목, 버튼에 가리지 않는 영역 (1080x1920 기준)
export const layout = {
  side: 80,
  headlineTop: 250,
  visualTop: 620,
  visualHeight: 600,
  captionTop: 1260,
};
