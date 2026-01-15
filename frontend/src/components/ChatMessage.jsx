import React from 'react';
import { Shield, Trello, Code, Activity, Calendar, Bot, User } from 'lucide-react';

export const ChatMessage = ({ msg }) => {
  const isUser = msg.type === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-slide-up`}>
      {/* Avatar */}
      <div className={`w-9 h-9 rounded-xl shrink-0 flex items-center justify-center shadow-soft ${isUser
          ? 'bg-gradient-to-br from-violet-500 to-indigo-600'
          : msg.isError
            ? 'bg-red-100 text-red-500'
            : 'bg-white border border-stone-200'
        }`}>
        {isUser ? (
          <User size={16} className="text-white" />
        ) : msg.isError ? (
          <span>⚠️</span>
        ) : (
          <Bot size={16} className="text-violet-500" />
        )}
      </div>

      {/* Message */}
      <div className={`flex flex-col max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${isUser
            ? 'bg-gradient-to-r from-violet-500 to-indigo-600 text-white rounded-tr-md'
            : msg.isError
              ? 'bg-red-50 text-red-700 border border-red-200 rounded-tl-md'
              : 'bg-white text-stone-700 shadow-soft rounded-tl-md'
          }`}>
          {msg.content}
        </div>

        {/* Rich Attachments */}
        {!isUser && msg.attachment && (
          <div className="mt-3 w-full">
            {msg.attachment.type === 'TICKET' && (
              <div className="bg-white border-l-4 border-orange-400 rounded-xl p-4 shadow-soft">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold flex items-center gap-2 text-stone-700 text-sm">
                    <Trello size={16} className="text-orange-500" />
                    {msg.attachment.data.ticket_id || 'TICKET'}
                  </span>
                  <span className="bg-orange-100 text-orange-600 px-2 py-1 rounded-lg text-xs font-medium">
                    {msg.attachment.data.status || 'TO DO'}
                  </span>
                </div>
                <p className="text-stone-600 text-sm mb-2">{msg.attachment.data.title}</p>
                <div className="flex gap-4 text-xs text-stone-400">
                  <span>Assignee: {msg.attachment.data.assignee}</span>
                  <span>Priority: {msg.attachment.data.priority}</span>
                </div>
              </div>
            )}

            {msg.attachment.type === 'CODE' && (
              <div className="bg-stone-800 text-stone-200 rounded-xl p-4 text-sm font-mono overflow-x-auto">
                <div className="flex justify-between items-center mb-3 border-b border-stone-700 pb-2">
                  <span className="flex items-center gap-2 text-violet-400">
                    <Code size={14} />
                    {msg.attachment.data.file}
                  </span>
                  <span className="text-xs text-stone-500">Lines {msg.attachment.data.lines || '??'}</span>
                </div>
                <pre className="whitespace-pre-wrap text-xs">{msg.attachment.data.snippet}</pre>
              </div>
            )}

            {msg.attachment.type === 'GANTT' && (
              <div className="bg-white rounded-xl p-4 shadow-soft">
                <div className="flex items-center gap-2 mb-4 font-semibold text-stone-700 text-sm">
                  <Activity size={16} className="text-blue-500" />
                  Project Roadmap
                </div>
                <div className="space-y-2">
                  {msg.attachment.data.tasks?.map((task, i) => (
                    <div key={i} className="relative h-8 bg-stone-100 rounded-lg overflow-hidden">
                      <div
                        className="absolute h-full bg-gradient-to-r from-violet-400 to-indigo-500 flex items-center pl-3 text-white text-xs font-medium rounded-lg"
                        style={{ width: `${task.progress}%` }}
                      >
                        {task.name}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {msg.attachment.type === 'CALENDAR' && (
              <div className="bg-white rounded-xl p-4 shadow-soft">
                <div className="flex items-center gap-2 mb-3 font-semibold text-stone-700 text-sm">
                  <Calendar size={16} className="text-emerald-500" />
                  Available Times
                </div>
                <div className="flex gap-2">
                  {msg.attachment.data.slots?.map((slot, i) => (
                    <button key={i} className="flex-1 py-3 px-4 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl text-center hover:bg-emerald-100 transition-colors text-sm font-medium">
                      {slot}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sources */}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {msg.sources.slice(0, 3).map((source, i) => (
              <span key={i} className="px-3 py-1.5 bg-violet-50 text-violet-600 rounded-lg text-xs font-medium">
                📄 {source.document} (p.{source.page})
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
