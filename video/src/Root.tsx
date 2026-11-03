import { Composition } from "remotion";
import { shortSchema } from "./schema";
import { calculateShortMetadata, Short } from "./Short";

// 실제 렌더링은 shorts.py가 --props로 대본, 음성, 자막 타이밍을 넘겨준다.
// defaultProps는 Studio 미리보기용 샘플이다.
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Short"
      component={Short}
      schema={shortSchema}
      calculateMetadata={calculateShortMetadata}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        channel: "itgony",
        source: "출처: GeekNews · news.hada.io",
        scenes: [
          {
            headline: "학습 0번",
            narration: "학습을 한 번도 안 했는데 성능이 올랐습니다.",
            audio: "sample/silence.mp3",
            durationInFrames: 90,
            words: [
              { text: "학습을", startMs: 0, endMs: 500 },
              { text: "한", startMs: 500, endMs: 700 },
              { text: "번도", startMs: 700, endMs: 1100 },
              { text: "안", startMs: 1100, endMs: 1300 },
              { text: "했는데", startMs: 1300, endMs: 1800 },
              { text: "성능이", startMs: 1800, endMs: 2300 },
              { text: "올랐습니다.", startMs: 2300, endMs: 2900 },
            ],
            visual: { type: "number", value: "0.016%", label: "수정한 가중치 비율" },
          },
          {
            headline: "AI가 AI를 수술",
            narration: "모델이 다른 모델의 가중치를 직접 읽고 고쳤습니다.",
            audio: "sample/silence.mp3",
            durationInFrames: 120,
            words: [
              { text: "모델이", startMs: 0, endMs: 500 },
              { text: "다른", startMs: 500, endMs: 900 },
              { text: "모델의", startMs: 900, endMs: 1400 },
              { text: "가중치를", startMs: 1400, endMs: 2000 },
              { text: "직접", startMs: 2000, endMs: 2400 },
              { text: "읽고", startMs: 2400, endMs: 2800 },
              { text: "고쳤습니다.", startMs: 2800, endMs: 3600 },
            ],
            visual: { type: "flow", items: ["가중치 읽기", "기능 위치 찾기", "0.016% 수정", "점수 상승"] },
          },
          {
            headline: "AI값 > 직원 보수?",
            narration: "여러분 생각은 어떠세요?",
            audio: "sample/silence.mp3",
            durationInFrames: 90,
            words: [
              { text: "여러분", startMs: 0, endMs: 500 },
              { text: "생각은", startMs: 500, endMs: 1000 },
              { text: "어떠세요?", startMs: 1000, endMs: 1700 },
            ],
            visual: { type: "none" },
          },
        ],
      }}
    />
  );
};
