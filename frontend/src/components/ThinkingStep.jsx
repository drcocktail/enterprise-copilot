import React from 'react';
import { CheckCircle, XOctagon } from 'lucide-react';

const ThinkingStep = ({ text, state }) => (
    <div className="flex items-center space-x-3 text-xs py-1">
        <div className="w-4 flex justify-center">
            {state === 'done' && <CheckCircle className="w-3.5 h-3.5 text-green-500" />}
            {state === 'error' && <XOctagon className="w-3.5 h-3.5 text-red-500" />}
            {state === 'processing' && <div className="w-2.5 h-2.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>}
            {state === 'waiting' && <div className="w-1.5 h-1.5 bg-slate-700 rounded-full"></div>}
        </div>
        <span className={`${state === 'done' ? 'text-slate-400' :
                state === 'error' ? 'text-red-400' :
                    state === 'processing' ? 'text-blue-400 font-medium' :
                        'text-slate-600'
            }`}>
            {text}
        </span>
    </div>
);

export default ThinkingStep;
