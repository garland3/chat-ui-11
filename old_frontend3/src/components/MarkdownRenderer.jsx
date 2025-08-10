import React, {useState} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeHighlight from 'rehype-highlight';
import '../styles/highlight.css';   // e.g. @import 'highlight.js/styles/github-dark.css';
import '../styles/markdown.css';    // your compact spacing rules

// Helpers
const extractText = n => n==null ? '' : (typeof n==='string'||typeof n==='number') ? String(n) : Array.isArray(n.props?.children) ? n.props.children.map(extractText).join('') : extractText(n.props?.children);
const parseMeta = m => { if(!m) return {}; const o={}; m.split(/\s+/).forEach(p=>{const[k,v]=p.split('='); if(k&&v) o[k]=v.replace(/^"|"$/g,'');}); return o; };
const langFromClass = cls => (String(cls||'').split(/\s+/).find(c=>c.startsWith('language-'))||'language-text').slice(9);

const InlineCode = ({children}) => (
  <code className="bg-zinc-800 border border-zinc-700 rounded px-1 py-0.5 text-[0.9em] font-mono">{children}</code>
);

function CodeBlock({className, children, metastring}) {
  const [copied,setCopied]=useState(false);
  const [wrap,setWrap]=useState(false);
  const lang=langFromClass(className);
  const meta=parseMeta(metastring);
  const raw=extractText(children);
  const onCopy=async()=>{await navigator.clipboard.writeText(raw); setCopied(true); setTimeout(()=>setCopied(false),800);};
  return (
    <div className="codeblock border border-zinc-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1 bg-zinc-900/70 border-b border-zinc-800">
        <div className="text-[11px] text-gray-300 flex items-center gap-2">
          <span className="uppercase tracking-wide">{lang}</span>
          {meta.title && <span className="text-gray-400">• {meta.title}</span>}
        </div>
        <div className="flex gap-2">
          <button onClick={()=>setWrap(w=>!w)} className="bg-zinc-700 hover:bg-zinc-600 px-2 py-0.5 rounded text-[11px]">{wrap?'No wrap':'Wrap'}</button>
          <button onClick={onCopy} className="bg-zinc-700 hover:bg-zinc-600 px-2 py-0.5 rounded text-[11px]">{copied?'Copied':'Copy'}</button>
        </div>
      </div>
      <pre className={`bg-[#0b0e14] text-zinc-100 p-3 overflow-x-auto ${wrap?'whitespace-pre-wrap break-words':'whitespace-pre'}`}>
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
}

export default function MarkdownRenderer({content}) {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl px-6 py-5">
        <ReactMarkdown
          className="markdown"
          remarkPlugins={[remarkGfm, remarkBreaks]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            code({inline,className,children,...props}) {
              if (inline) return <InlineCode {...props}>{children}</InlineCode>;
              return <code className={className} {...props}>{children}</code>;
            },
            pre({children}) {
              const codeEl = Array.isArray(children)?children[0]:children;
              const className = codeEl?.props?.className||'';
              const metastring = codeEl?.props?.metastring||codeEl?.props?.['data-meta']||'';
              return <CodeBlock className={className} metastring={metastring}>{codeEl?.props?.children}</CodeBlock>;
            },
            h1: ({children}) => <h1 className="text-[24px] font-semibold mt-5 first:mt-0 mb-2 leading-tight">{children}</h1>,
            h2: ({children}) => <h2 className="text-[20px] font-semibold mt-4 mb-1 leading-tight">{children}</h2>,
            h3: ({children}) => <h3 className="text-[17px] font-semibold mt-3 mb-1 leading-snug">{children}</h3>,
            p:  ({children, ...props}) => {
              // Check if this paragraph is inside a list item by checking parent
              const isInListItem = props.node?.parent?.tagName === 'li';
              console.log('Paragraph component:', { 
                isInListItem, 
                parentTag: props.node?.parent?.tagName,
                parentType: props.node?.parent?.type,
                nodeType: props.node?.type,
                children: typeof children === 'string' ? children.substring(0, 50) : 'complex'
              });
              return <p className={`text-zinc-200 leading-[1.55] ${isInListItem ? 'inline m-0' : 'mb-2 last:mb-0'}`}>{children}</p>;
            },
            ul: ({children}) => <ul className="list-disc pl-5 mb-2 marker:text-zinc-500 space-y-1 last:mb-0">{children}</ul>,
            ol: ({children}) => <ol className="list-decimal pl-5 mb-2 marker:text-zinc-500 space-y-1 last:mb-0">{children}</ol>,
            li: ({children}) => <li className="leading-6">{children}</li>,
            blockquote: ({children}) => <blockquote className="border-l-2 border-zinc-700 pl-3 italic text-zinc-300">{children}</blockquote>,
            table: ({children}) => <div><table className="min-w-full border border-zinc-800 rounded-lg">{children}</table></div>,
            th: ({children}) => <th className="border border-zinc-800 px-3 py-2 bg-zinc-800/60 text-left">{children}</th>,
            td: ({children}) => <td className="border border-zinc-800 px-3 py-2">{children}</td>,
            a:  ({children,href}) => <a href={href} className="text-sky-400 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
            hr: () => <hr className="border-zinc-800"/>,
            strong: ({children}) => <strong className="font-semibold">{children}</strong>,
            em: ({children}) => <em className="italic">{children}</em>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
