import { Composition } from "remotion";
import { shortSchema } from "./schema";
import { calculateShortMetadata, Short } from "./Short";

// 실제 렌더링은 shorts.py가 --props로 대본, 음성, 컷·자막 타이밍을 넘겨준다.
// defaultProps는 Studio 미리보기용 샘플이다. (효과음은 shorts.py 실행 시 public/sfx에 생성됨)
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Short"
      component={Short}
      schema={shortSchema}
      calculateMetadata={calculateShortMetadata}
      durationInFrames={150}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        channel: "itgony",
        source: "출처: GeekNews · news.hada.io",
        audio: "sample/silence.mp3",
        durationInFrames: 150,
        sfx: [],
        cuts: [
          {
            from: 0,
            durationInFrames: 45,
            visual: { type: "hook", value: "학습 0번" },
            chunks: [
              { text: "학습", from: 0, durationInFrames: 20, emphasis: false },
              { text: "0번.", from: 20, durationInFrames: 25, emphasis: true },
            ],
          },
          {
            from: 45,
            durationInFrames: 55,
            visual: { type: "number", value: "0.016%", label: "수정한 가중치" },
            chunks: [
              { text: "딱 0.016%만", from: 0, durationInFrames: 25, emphasis: true },
              { text: "고쳤대요", from: 25, durationInFrames: 30, emphasis: false },
            ],
          },
          {
            from: 100,
            durationInFrames: 50,
            visual: { type: "none" },
            chunks: [
              { text: "근데", from: 0, durationInFrames: 20, emphasis: false },
              { text: "점수가 올랐어요", from: 20, durationInFrames: 30, emphasis: true },
            ],
          },
        ],
      }}
    />
  );
};
