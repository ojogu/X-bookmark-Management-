export function Wordmark() {
  return (
    <span className="wordmark">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="200"
        height="40"
        viewBox="0 0 200 40"
        className="wordmark-dark"
      >
        <rect x="0" y="8" width="24" height="4" rx="1.5" fill="#1D9E75" opacity="0.4" />
        <rect x="0" y="16" width="24" height="4" rx="1.5" fill="#1D9E75" opacity="0.7" />
        <rect x="0" y="24" width="24" height="4" rx="1.5" fill="#1D9E75" />
        <polygon points="18,24 24,24 24,28 21,26 18,28" fill="#ffffff" />
        <text x="34" y="30" fontFamily="Georgia, serif" fontSize="22" fontWeight="500" letterSpacing="-0.3">
          <tspan fill="#1D9E75">Save</tspan>
          <tspan fill="#ffffff">Stack</tspan>
        </text>
      </svg>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="200"
        height="40"
        viewBox="0 0 200 40"
        className="wordmark-light"
      >
        <rect x="0" y="8" width="24" height="4" rx="1.5" fill="#1D9E75" opacity="0.35" />
        <rect x="0" y="16" width="24" height="4" rx="1.5" fill="#1D9E75" opacity="0.65" />
        <rect x="0" y="24" width="24" height="4" rx="1.5" fill="#1D9E75" />
        <polygon points="18,24 24,24 24,28 21,26 18,28" fill="#111111" />
        <text x="34" y="30" fontFamily="Georgia, serif" fontSize="22" fontWeight="500" letterSpacing="-0.3">
          <tspan fill="#1D9E75">Save</tspan>
          <tspan fill="#111111">Stack</tspan>
        </text>
      </svg>
    </span>
  )
}