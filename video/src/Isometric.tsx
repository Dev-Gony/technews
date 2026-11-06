import { colors } from "./theme";

// 아이소메트릭(30도) 도형 도우미 + 비유 그림에 올리는 사물 아이콘.
// 좌표: x(오른쪽 아래), y(왼쪽 아래), z(위). 단위 u = 픽셀 크기 기준.

export const ICONS = [
  "server", "gpu", "cloud", "database", "robot", "person",
  "laptop", "document", "coins", "truck", "lock", "building",
] as const;

export type IconName = (typeof ICONS)[number];

const COS = Math.cos(Math.PI / 6);
const SIN = 0.5;

export type Shade = { top: string; left: string; right: string };

// 기본 색 3단 음영 (윗면 밝게, 왼쪽 중간, 오른쪽 어둡게)
export const shades = {
  paper: { top: "#F2EEE3", left: "#CFCABD", right: "#A9A497" },
  steel: { top: "#5A5750", left: "#45433D", right: "#33312D" },
  ink: { top: "#34322D", left: "#26241F", right: "#1B1A17" },
  red: { top: "#F06A5C", left: "#D14335", right: "#A8342A" },
  gold: { top: "#FFD47A", left: "#E8B040", right: "#B98A2C" },
  screen: { top: "#9FD8FF", left: "#6DB6E8", right: "#4E8FBF" },
};

const project = (u: number, x: number, y: number, z: number): [number, number] => [
  (x - y) * COS * u,
  (x + y) * SIN * u - z * u,
];

const pts = (list: [number, number][]) => list.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

// 직육면체: 보이는 세 면(윗면, 앞-왼쪽, 앞-오른쪽)만 그린다.
export const IsoBox: React.FC<{
  u: number;
  x: number;
  y: number;
  z: number;
  dx: number;
  dy: number;
  dz: number;
  shade: Shade;
}> = ({ u, x, y, z, dx, dy, dz, shade }) => {
  const p = (a: number, b: number, c: number) => project(u, a, b, c);
  const top = [p(x, y, z + dz), p(x + dx, y, z + dz), p(x + dx, y + dy, z + dz), p(x, y + dy, z + dz)];
  const left = [p(x, y + dy, z), p(x + dx, y + dy, z), p(x + dx, y + dy, z + dz), p(x, y + dy, z + dz)];
  const right = [p(x + dx, y, z), p(x + dx, y + dy, z), p(x + dx, y + dy, z + dz), p(x + dx, y, z + dz)];

  return (
    <g>
      <polygon points={pts(left)} style={{ fill: shade.left }} />
      <polygon points={pts(right)} style={{ fill: shade.right }} />
      <polygon points={pts(top)} style={{ fill: shade.top }} />
    </g>
  );
};

// 세운 원기둥 (가운데 cx, cy 기준, 반지름 r, 높이 h)
export const IsoCylinder: React.FC<{
  u: number;
  x: number;
  y: number;
  z: number;
  r: number;
  h: number;
  shade: Shade;
}> = ({ u, x, y, z, r, h, shade }) => {
  const [cx, cy] = project(u, x, y, z);
  const rx = r * u * 1.22;
  const ry = r * u * 0.71;
  const top = cy - h * u;

  return (
    <g>
      <path
        d={`M ${cx - rx} ${top} L ${cx - rx} ${cy} A ${rx} ${ry} 0 0 0 ${cx + rx} ${cy} L ${cx + rx} ${top} Z`}
        style={{ fill: shade.left }}
      />
      <path d={`M ${cx} ${top} L ${cx} ${cy + ry} A ${rx} ${ry} 0 0 0 ${cx + rx} ${cy} L ${cx + rx} ${top} Z`} style={{ fill: shade.right }} />
      <ellipse cx={cx} cy={top} rx={rx} ry={ry} style={{ fill: shade.top }} />
    </g>
  );
};

const Sphere: React.FC<{ u: number; x: number; y: number; z: number; r: number; fill: string }> = ({ u, x, y, z, r, fill }) => {
  const [cx, cy] = project(u, x, y, z);

  return <circle cx={cx} cy={cy} r={r * u} style={{ fill }} />;
};

// 사물 아이콘. 바닥 판(0~1 x 0~1) 가운데에 올라간다. main이면 브랜드 빨강을 쓴다.
export const IsoIcon: React.FC<{ name: string; u: number; main: boolean }> = ({ name, u, main }) => {
  const body = main ? shades.red : shades.paper;
  const dark = shades.ink;

  switch (name as IconName) {
    case "server":
      return (
        <g>
          <IsoBox u={u} x={0.3} y={0.3} z={0} dx={0.4} dy={0.4} dz={1.1} shade={body} />
          {[0.25, 0.5, 0.75, 1.0].map((level) => (
            <IsoBox key={level} u={u} x={0.3} y={0.7} z={level - 0.06} dx={0.4} dy={0.001} dz={0.04} shade={dark} />
          ))}
          {[0.3, 0.55, 0.8].map((level) => (
            <Sphere key={level} u={u} x={0.38} y={0.7} z={level - 0.12} r={0.025} fill={colors.gold} />
          ))}
        </g>
      );
    case "gpu":
      return (
        <g>
          <IsoBox u={u} x={0.12} y={0.25} z={0} dx={0.76} dy={0.5} dz={0.16} shade={main ? shades.red : shades.steel} />
          <IsoCylinder u={u} x={0.32} y={0.5} z={0.16} r={0.13} h={0.03} shade={dark} />
          <IsoCylinder u={u} x={0.68} y={0.5} z={0.16} r={0.13} h={0.03} shade={dark} />
          {[0.2, 0.35, 0.5, 0.65, 0.8].map((x) => (
            <IsoBox key={x} u={u} x={x} y={0.75} z={0} dx={0.06} dy={0.06} dz={0.06} shade={shades.gold} />
          ))}
        </g>
      );
    case "cloud":
      return (
        <g>
          <Sphere u={u} x={0.3} y={0.55} z={0.5} r={0.22} fill={main ? shades.red.left : shades.paper.left} />
          <Sphere u={u} x={0.72} y={0.35} z={0.52} r={0.22} fill={main ? shades.red.left : shades.paper.left} />
          <Sphere u={u} x={0.5} y={0.42} z={0.72} r={0.3} fill={main ? shades.red.top : shades.paper.top} />
          <Sphere u={u} x={0.62} y={0.62} z={0.42} r={0.24} fill={main ? shades.red.right : shades.paper.right} />
        </g>
      );
    case "database":
      return (
        <g>
          {[0, 0.32, 0.64].map((z) => (
            <IsoCylinder key={z} u={u} x={0.5} y={0.5} z={z} r={0.3} h={0.26} shade={body} />
          ))}
        </g>
      );
    case "robot":
      return (
        <g>
          <IsoBox u={u} x={0.3} y={0.3} z={0} dx={0.4} dy={0.4} dz={0.5} shade={body} />
          <IsoBox u={u} x={0.33} y={0.33} z={0.56} dx={0.34} dy={0.34} dz={0.3} shade={body} />
          <Sphere u={u} x={0.42} y={0.67} z={0.73} r={0.04} fill={colors.gold} />
          <Sphere u={u} x={0.58} y={0.67} z={0.73} r={0.04} fill={colors.gold} />
          <IsoBox u={u} x={0.48} y={0.48} z={0.86} dx={0.04} dy={0.04} dz={0.16} shade={dark} />
          <Sphere u={u} x={0.5} y={0.5} z={1.06} r={0.05} fill={colors.gold} />
        </g>
      );
    case "person":
      return (
        <g>
          <IsoCylinder u={u} x={0.5} y={0.5} z={0} r={0.2} h={0.55} shade={body} />
          <Sphere u={u} x={0.5} y={0.5} z={0.78} r={0.17} fill={main ? shades.red.top : shades.paper.top} />
        </g>
      );
    case "laptop":
      return (
        <g>
          <IsoBox u={u} x={0.2} y={0.2} z={0.55} dx={0.6} dy={0.04} dz={0.001} shade={dark} />
          <IsoBox u={u} x={0.2} y={0.16} z={0.04} dx={0.6} dy={0.04} dz={0.5} shade={main ? shades.red : shades.steel} />
          <IsoBox u={u} x={0.24} y={0.2} z={0.08} dx={0.52} dy={0.001} dz={0.42} shade={shades.screen} />
          <IsoBox u={u} x={0.2} y={0.2} z={0} dx={0.6} dy={0.6} dz={0.04} shade={main ? shades.red : shades.steel} />
        </g>
      );
    case "document":
      return (
        <g>
          <IsoBox u={u} x={0.3} y={0.45} z={0} dx={0.45} dy={0.04} dz={0.85} shade={body} />
          {[0.65, 0.52, 0.39, 0.26].map((z) => (
            <IsoBox key={z} u={u} x={0.36} y={0.49} z={z} dx={0.33} dy={0.001} dz={0.035} shade={dark} />
          ))}
        </g>
      );
    case "coins":
      return (
        <g>
          {[0, 0.12, 0.24, 0.36].map((z) => (
            <IsoCylinder key={`a${z}`} u={u} x={0.38} y={0.4} z={z} r={0.2} h={0.1} shade={shades.gold} />
          ))}
          {[0, 0.12, 0.24, 0.36, 0.48, 0.6].map((z) => (
            <IsoCylinder key={`b${z}`} u={u} x={0.68} y={0.62} z={z} r={0.2} h={0.1} shade={shades.gold} />
          ))}
        </g>
      );
    case "truck":
      return (
        <g>
          <IsoBox u={u} x={0.08} y={0.3} z={0.12} dx={0.56} dy={0.42} dz={0.48} shade={body} />
          <IsoBox u={u} x={0.66} y={0.3} z={0.12} dx={0.26} dy={0.42} dz={0.32} shade={main ? shades.paper : shades.steel} />
          <IsoBox u={u} x={0.92} y={0.36} z={0.26} dx={0.001} dy={0.3} dz={0.14} shade={shades.screen} />
          {[0.22, 0.52, 0.8].map((x) => (
            <Sphere key={x} u={u} x={x} y={0.74} z={0.1} r={0.1} fill="#141412" />
          ))}
        </g>
      );
    case "lock": {
      const [cx, cy] = project(u, 0.5, 0.5, 0.62);

      return (
        <g>
          <path
            d={`M ${cx - 0.17 * u} ${cy} L ${cx - 0.17 * u} ${cy - 0.18 * u} A ${0.17 * u} ${0.2 * u} 0 0 1 ${cx + 0.17 * u} ${cy - 0.18 * u} L ${cx + 0.17 * u} ${cy}`}
            style={{ fill: "none", stroke: shades.steel.top }}
            strokeWidth={0.07 * u}
          />
          <IsoBox u={u} x={0.28} y={0.32} z={0} dx={0.44} dy={0.36} dz={0.55} shade={main ? shades.red : shades.gold} />
        </g>
      );
    }
    case "building":
    default:
      return (
        <g>
          <IsoBox u={u} x={0.22} y={0.25} z={0} dx={0.56} dy={0.5} dz={0.55} shade={body} />
          {[0.3, 0.5].map((x) => (
            <IsoBox key={x} u={u} x={x} y={0.75} z={0.22} dx={0.12} dy={0.001} dz={0.18} shade={shades.screen} />
          ))}
          <IsoBox u={u} x={0.18} y={0.21} z={0.55} dx={0.64} dy={0.58} dz={0.06} shade={dark} />
        </g>
      );
  }
};

// 아이콘을 올리는 얇은 바닥 판
export const IsoPlate: React.FC<{ u: number; main: boolean }> = ({ u, main }) => (
  <IsoBox u={u} x={-0.08} y={-0.08} z={-0.12} dx={1.16} dy={1.16} dz={0.12} shade={main ? shades.ink : shades.ink} />
);

export const isoProject = project;
