import { useState, useEffect } from 'react';
import { Timer } from 'lucide-react';

export default function CountdownTimer({ nextCheck, interval, isRunning }) {
  const [timeLeft, setTimeLeft] = useState(null);

  useEffect(() => {
    if (!nextCheck || !isRunning) {
      setTimeLeft(null);
      return;
    }

    const updateCountdown = () => {
      const now = Date.now();
      const next = new Date(nextCheck).getTime();
      const diff = Math.max(0, next - now);
      setTimeLeft(diff);
    };

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [nextCheck, isRunning]);

  if (!isRunning) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-surface-200/40">
        <span className="w-1.5 h-1.5 rounded-full bg-surface-200/30" />
        Inactivo
      </span>
    );
  }

  if (timeLeft === null) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-emerald-400">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
        Activo
      </span>
    );
  }

  const totalSeconds = Math.ceil(timeLeft / 1000);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  const isImminent = totalSeconds <= 10;

  return (
    <div className="flex items-center gap-2">
      {/* Active indicator */}
      <span className="flex items-center gap-1.5 text-xs text-emerald-400">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
        Activo
      </span>

      {/* Divider */}
      <span className="w-px h-4 bg-surface-700/60" />

      {/* Countdown */}
      <div className={`flex items-center gap-1.5 text-xs font-medium transition-colors
                       ${isImminent ? 'text-amber-400' : 'text-surface-200/60'}`}>
        <Timer size={12} className={isImminent ? 'animate-pulse' : ''} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
          {mins > 0 ? `${mins}m ${String(secs).padStart(2, '0')}s` : `${secs}s`}
        </span>
      </div>

      {/* Progress ring */}
      <svg width="20" height="20" viewBox="0 0 20 20" className="flex-shrink-0 -ml-0.5">
        <circle
          cx="10" cy="10" r="8"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-surface-700/40"
        />
        <circle
          cx="10" cy="10" r="8"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          className={isImminent ? 'text-amber-400' : 'text-brand-500'}
          strokeDasharray={`${2 * Math.PI * 8}`}
          strokeDashoffset={`${2 * Math.PI * 8 * (1 - (totalSeconds / ((interval || 1) * 60)))}`}
          style={{
            transform: 'rotate(-90deg)',
            transformOrigin: '50% 50%',
            transition: 'stroke-dashoffset 1s linear',
          }}
        />
      </svg>
    </div>
  );
}
