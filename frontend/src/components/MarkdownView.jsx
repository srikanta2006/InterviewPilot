import { useMemo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import './MarkdownView.css'

marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * Normalizes raw LLM output or plain text into clean, structured Markdown.
 * Ensures section headers, scenarios, and bullet lists break into distinct paragraphs
 * instead of running together as a single text block.
 */
function normalizeMarkdown(text) {
  if (!text || typeof text !== 'string') return ''

  let normalized = text.replace(/\r\n/g, '\n').trim()

  // Ensure double newlines before common interview section prefixes so they break out of lists or previous blocks
  const headerRegex = /(?:\n)*(\*\*(?:Scenario|Context|Problem Statement|Technical Challenge|Technical Constraints|Requirements|Key Considerations|Key Requirements|Question|Your Task):?\*\*|###\s+(?:Scenario|Context|Problem|Question))/gi

  normalized = normalized.replace(headerRegex, '\n\n$1').trim()

  // Ensure double newlines after bullet list blocks before subsequent paragraphs
  normalized = normalized.replace(/(\n[*-]\s+[^\n]+)\n([A-Z*#])/g, '$1\n\n$2')

  return normalized
}

export function MarkdownView({ content = '', className = '' }) {
  const renderedHtml = useMemo(() => {
    if (!content) return ''
    try {
      const cleanContent = normalizeMarkdown(content)
      const rawHtml = marked.parse(cleanContent)
      return DOMPurify.sanitize(rawHtml)
    } catch {
      return content
    }
  }, [content])

  return (
    <div
      className={`markdown-view ${className}`}
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  )
}
