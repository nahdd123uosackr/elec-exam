'use client'

import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

// 마크다운 + 수식(LaTeX/KaTeX)을 HTML로 깔끔하게 렌더링 (ChatBot, ProblemCard 공용)
export default function MarkdownMessage({ content, className = '' }: { content: string; className?: string }) {
  return (
    <div className={`markdown-body text-sm leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          h1: ({ children }) => <h1 className="text-base font-bold mt-3 mb-1.5 first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-bold mt-3 mb-1.5 first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-bold mt-2.5 mb-1 first:mt-0">{children}</h3>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          code: ({ children }) => <code className="bg-gray-200 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
          pre: ({ children }) => <pre className="bg-gray-800 text-gray-100 rounded-lg p-3 mb-2 overflow-x-auto text-xs">{children}</pre>,
          blockquote: ({ children }) => <blockquote className="border-l-2 border-gray-300 pl-3 my-2 text-gray-600 italic">{children}</blockquote>,
          hr: () => <hr className="my-3 border-gray-300" />,
          table: ({ children }) => <div className="overflow-x-auto mb-2"><table className="min-w-full text-xs border-collapse">{children}</table></div>,
          th: ({ children }) => <th className="border border-gray-300 px-2 py-1 bg-gray-100 font-semibold text-left">{children}</th>,
          td: ({ children }) => <td className="border border-gray-300 px-2 py-1">{children}</td>,
          a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="text-blue-600 underline">{children}</a>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
