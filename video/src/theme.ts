import { loadFont } from "@remotion/google-fonts/NotoSansKR";

export const { fontFamily } = loadFont("normal", {
  weights: ["500", "700", "900"],
  subsets: ["korean", "latin"],
});

export const colors = {
  background: "#0B0E14",
  surface: "rgba(255, 255, 255, 0.07)",
  border: "rgba(255, 255, 255, 0.14)",
  text: "#F5F6F8",
  muted: "#9AA2AE",
  accent: "#FF5C4D",
  accentSoft: "rgba(255, 92, 77, 0.2)",
  highlight: "#FFD84D",
  blue: "#4D8DFF",
  green: "#3DDC97",
};

// Shorts 화면에서 제목, 버튼에 가리지 않는 영역 (1080x1920 기준)
export const layout = {
  side: 80,
  visualTop: 330,
  visualHeight: 680,
  captionTop: 1110,
};
