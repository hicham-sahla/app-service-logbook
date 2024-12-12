const parser = new DOMParser();

export function HtmlToReadableText(html: string): string {
  const doc = parser.parseFromString(html, 'text/html');
  return Array.from(doc.body.children)
    .map(el => (el as HTMLElement).innerText)
    .join(' ');
}
