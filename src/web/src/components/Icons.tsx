// Small inline stroke icons (decorative; always aria-hidden).
import type { ReactNode } from "react";

function Svg({ size = 18, children }: { size?: number; children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const CapIcon = ({ size = 22 }: { size?: number }) => (
  <Svg size={size}>
    <path d="M3 7l9-4 9 4-9 4-9-4z" />
    <path d="M7 9.5V15c0 1.5 2.2 3 5 3s5-1.5 5-3V9.5" />
  </Svg>
);
export const CheckIcon = () => (
  <Svg>
    <path d="M20 6L9 17l-5-5" />
  </Svg>
);
export const LockIcon = () => (
  <Svg>
    <rect x="5" y="11" width="14" height="10" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </Svg>
);
export const ArrowIcon = () => (
  <Svg size={16}>
    <path d="M5 12h14" />
    <path d="M13 6l6 6-6 6" />
  </Svg>
);
export const AlertIcon = () => (
  <Svg>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v5" />
    <path d="M12 16h.01" />
  </Svg>
);
export const CloseIcon = () => (
  <Svg size={16}>
    <path d="M6 6l12 12" />
    <path d="M18 6L6 18" />
  </Svg>
);
export const EyeIcon = () => (
  <Svg size={20}>
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
    <circle cx="12" cy="12" r="3" />
  </Svg>
);
export const UserIcon = () => (
  <Svg>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
  </Svg>
);
export const StarIcon = () => (
  <Svg size={16}>
    <path d="M12 3l1.9 5.6L20 9.3l-4.6 3.7L17 19l-5-3.2L7 19l1.6-6L4 9.3l6.1-.7z" />
  </Svg>
);
export const SparkIcon = () => (
  <Svg size={16}>
    <path d="M12 3v4" />
    <path d="M12 17v4" />
    <path d="M3 12h4" />
    <path d="M17 12h4" />
    <path d="M6.5 6.5l2.5 2.5" />
    <path d="M15 15l2.5 2.5" />
    <path d="M17.5 6.5L15 9" />
    <path d="M9 15l-2.5 2.5" />
  </Svg>
);
