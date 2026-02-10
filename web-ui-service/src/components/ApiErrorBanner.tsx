import { useEffect, useState } from 'react';
import { isUsingMockData, getLastApiError } from '../services/api';

/**
 * Displays a warning banner when the backend is unreachable
 * and the UI is falling back to mock/demo data.
 */
export default function ApiErrorBanner() {
  const [visible, setVisible] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Poll the fallback flag every 3 seconds
    const check = () => {
      const isMock = isUsingMockData();
      setVisible(isMock);
      setMessage(getLastApiError());
    };
    check();
    const id = setInterval(check, 3000);
    return () => clearInterval(id);
  }, []);

  if (!visible) return null;

  return (
    <div className="bg-yellow-900/80 border border-yellow-600 text-yellow-200 px-4 py-2 text-sm flex items-center gap-2 justify-between">
      <span>
        ⚠️ <strong>Backend unreachable</strong> — displaying demo data.
        {message ? ` (${message})` : ''}
      </span>
      <button
        onClick={() => setVisible(false)}
        className="text-yellow-400 hover:text-yellow-100 font-bold ml-2"
      >
        ✕
      </button>
    </div>
  );
}
