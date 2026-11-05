// Bộ icon nét mảnh 20px (vẽ tay theo lưới 24). Luôn đi kèm chữ, nên mặc định aria-hidden.
import type { ReactNode, SVGProps } from "react";

function Svg({ children, ...rest }: SVGProps<SVGSVGElement> & { children: ReactNode }) {
  return (
    <svg
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const IconUser = () => (
  <Svg>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
  </Svg>
);
export const IconList = () => (
  <Svg>
    <path d="M9 6h11M9 12h11M9 18h11" />
    <path d="M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2" />
  </Svg>
);
export const IconSparkle = () => (
  <Svg>
    <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
    <path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z" />
  </Svg>
);
export const IconCalendar = () => (
  <Svg>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 10h18M8 3v4M16 3v4" />
  </Svg>
);
export const IconGraph = () => (
  <Svg>
    <circle cx="5" cy="6" r="2" />
    <circle cx="5" cy="18" r="2" />
    <circle cx="19" cy="12" r="2" />
    <path d="M7 6.5l10 5M7 17.5l10-5" />
  </Svg>
);
export const IconBook = () => (
  <Svg>
    <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" />
    <path d="M4 19V5M8 7h7" />
  </Svg>
);
export const IconAlert = () => (
  <Svg>
    <path d="M12 3l9.5 17h-19z" />
    <path d="M12 10v4M12 17.5v.01" />
  </Svg>
);
export const IconSearch = () => (
  <Svg>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </Svg>
);
export const IconPlus = () => (
  <Svg>
    <path d="M12 5v14M5 12h14" />
  </Svg>
);
export const IconCheck = () => (
  <Svg>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Svg>
);
export const IconArrowRight = () => (
  <Svg>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Svg>
);
export const IconSliders = () => (
  <Svg>
    <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0" />
    <circle cx="16" cy="6" r="2" />
    <circle cx="10" cy="12" r="2" />
    <circle cx="18" cy="18" r="2" />
  </Svg>
);
