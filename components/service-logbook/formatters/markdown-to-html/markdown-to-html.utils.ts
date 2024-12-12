import MarkdownIt from 'markdown-it';

export function renderMarkdownToHtml(markdown: string): string {
  const markdownIt = new MarkdownIt({
    typographer: true,
  });

  // Add target='_blank' to links.
  // See https://github.com/markdown-it/markdown-it/blob/master/docs/architecture.md#renderer
  const defaultRender =
    markdownIt.renderer.rules.link_open ||
    function (tokens, idx, options, env, self) {
      return self.renderToken(tokens, idx, options);
    };
  markdownIt.renderer.rules.link_open = function (tokens, idx, options, env, self) {
    tokens[idx].attrPush(['target', '_blank']);
    return defaultRender(tokens, idx, options, env, self);
  };

  return markdownIt.render(markdown);
}
