// Icon components for Vermont Signal

export function MountainIcon({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M2 20L9 8L14 14L22 4V20H2Z"
        fill="currentColor"
        fillOpacity="0.9"
      />
      <path
        d="M2 20L9 8L14 14L22 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SignalWavesIcon({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="2" fill="currentColor"/>
      <path
        d="M8 12C8 9.79086 9.79086 8 12 8C14.2091 8 16 9.79086 16 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M5 12C5 8.13401 8.13401 5 12 5C15.866 5 19 8.13401 19 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function MapleLeafIcon({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L13.5 7H10.5L12 2Z"
        fill="currentColor"
      />
      <path
        d="M12 7L9 9L11 10L9 12L12 11L15 12L13 10L15 9L12 7Z"
        fill="currentColor"
      />
      <path
        d="M12 11L10 16L12 15L12 22L12 15L14 16L12 11Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function PineTreeIcon({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L8 8H10L7 13H9L5 19H19L15 13H17L14 8H16L12 2Z"
        fill="currentColor"
      />
      <rect x="11" y="19" width="2" height="3" fill="currentColor"/>
    </svg>
  );
}

export function VermontOutlineIcon({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M16 2L17 4L18 2L18 20L17 22L7 22L6 20L6 4L7 2L16 2Z"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="currentColor"
        fillOpacity="0.2"
      />
    </svg>
  );
}
