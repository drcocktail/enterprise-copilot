import React from 'react';
import { Shield } from 'lucide-react';

export const IAMBadge = ({ role, permissions }) => (
  <div className="flex items-center gap-2 text-xs font-medium bg-stone-100 p-2.5 rounded-xl text-stone-500">
    <Shield size={14} className="text-violet-500" />
    <span className="text-stone-400">Role:</span>
    <span className="text-violet-600">{role?.replace(/_/g, ' ')}</span>
    <span className="text-stone-300">•</span>
    <span className="text-stone-400">{permissions?.length || 0} permissions</span>
  </div>
);
