import { Composition } from "remotion";
import { Cards, calculateCardsMetadata } from "./cards/Cards";
import { cardsSchema } from "./cards/schema";
import { shortSchema } from "./schema";
import { calculateShortMetadata, Short } from "./Short";

// 실제 렌더링은 shorts.py / cards.py가 --props로 내용을 넘겨준다.
// defaultProps는 Studio 미리보기용 샘플이다. (효과음은 shorts.py 실행 시 public/sfx에 생성됨)
export const RemotionRoot: React.FC = () => {
  return (
    <>
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
          cover: "학습 없이\n성능 상승?",
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
              visual: { type: "code", code: "~/.ssh/authorized_keys\n+ 공격자 키 추가됨" },
              chunks: [
                { text: "근데", from: 0, durationInFrames: 20, emphasis: false },
                { text: "점수가 올랐어요", from: 20, durationInFrames: 30, emphasis: true },
              ],
            },
          ],
        }}
      />
      {/* 인스타그램 카드뉴스 (1080x1350, 프레임 하나 = 카드 한 장) */}
      <Composition
        id="Cards"
        component={Cards}
        schema={cardsSchema}
        calculateMetadata={calculateCardsMetadata}
        durationInFrames={7}
        fps={1}
        width={1080}
        height={1350}
        defaultProps={{
          masthead: "GONY DAILY",
          date: "2026.11.04",
          section: "AI · 비용",
          handle: "@itgony",
          source: "출처: GeekNews",
          slides: [
            {
              type: "cover",
              label: "AI · 비용",
              title: "AI 비용 **90%** 줄인\nRevolut의 선택",
              body: "외부 API를 끊고 GLM을 직접 돌렸다.\n핀테크가 자체 호스팅으로 간 이유.",
            },
            {
              type: "story",
              label: "무슨 일이 있었나",
              title: "빌려 쓰던 AI를\n직접 돌리기로",
              items: [
                "외부 AI API 대신 오픈 모델 GLM을 자체 서버에 올렸다",
                "엔비디아 B200 56대로 사내 전체 AI 작업을 처리",
                "비용 부담이 사라지자 모든 업무에 AI를 붙였다",
              ],
            },
            {
              type: "number",
              label: "핵심 숫자",
              value: "1/10",
              title: "토큰당 비용",
              body: "외부 API 대비 토큰당 비용이 10분의 1로 줄었다.",
            },
            {
              type: "flow",
              label: "어떻게 했나",
              title: "자체 호스팅으로 가는 길",
              items: ["외부 API 사용량·비용 측정", "오픈 모델 GLM 선택", "B200 56대에 직접 배포", "전 업무에 AI 적용"],
            },
            {
              type: "checklist",
              label: "바로 써먹는 법",
              title: "우리 팀도 따져보자",
              items: [
                "이번 달 AI API 청구서에서 토큰 단가와 사용량 뽑기",
                "자체 호스팅 시 GPU·운영 인력 비용까지 넣어 손익 계산",
                "비용 때문에 AI를 못 붙인 업무 목록 만들기",
              ],
            },
            {
              type: "caution",
              label: "주의",
              title: "싸 보여도 공짜는 아니다",
              body: "자체 호스팅은 GPU 구매·전기·운영 인력이 따로 든다. 사용량이 적으면 오히려 비싸다.",
            },
            {
              type: "outro",
              label: "여러분 생각은?",
              title: "우리 팀은\n직접 돌릴까,\n빌려 쓸까?",
              body: "저장해두고 다음 비용 회의 때 꺼내 보세요.",
            },
          ],
        }}
      />
    </>
  );
};
