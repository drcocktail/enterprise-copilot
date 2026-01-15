import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export const DashboardWidget = ({ title, value, trend, icon: Icon, color }) => {
  const isPositive = trend.startsWith('+') || trend === '0';

  return (
    <div className="bg-white p-6 rounded-2xl shadow-soft hover:shadow-soft-lg transition-all">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-stone-400">{title}</p>
          <h3 className="text-3xl font-bold text-stone-800 mt-1">{value}</h3>
        </div>
        <div className={`p-3 rounded-xl ${color} shadow-lg`}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 text-sm">
        <div className={`flex items-center gap-1 px-2.5 py-1 rounded-lg ${isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
          }`}>
          {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <span className="font-medium">{trend}</span>
        </div>
        <span className="text-stone-400">vs last month</span>
      </div>
    </div>
  );
};
