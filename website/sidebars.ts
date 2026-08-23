import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

/**
 * Flat docs IA (Task 19) — omp task-page model + pi.dev nav model.
 * 7 top-level categories, all collapsed, max 2 levels deep.
 * Every id below was verified against the current docs tree (no file moves —
 * see docs/MIGRATION-MAP.md for the old->new slot mapping).
 */
const sidebars: SidebarsConfig = {
  docs: [
    'user-stories',
    {
      type: 'category',
      label: 'Start here',
      collapsed: true,
      items: [
        'getting-started/quickstart',
        'getting-started/installation',
        'user-guide/cli',
        'integrations/providers',
        'user-guide/security',
        'user-guide/configuration',
        'user-guide/tui',
        'user-guide/sessions',
        'developer-guide/context-compression-and-caching',
      ],
    },
    {
      type: 'category',
      label: 'Features',
      collapsed: true,
      items: [
        'user-guide/features/memory',
        'user-guide/features/delegation',
        'user-guide/features/skills',
        'user-guide/features/hooks',
        'user-guide/features/tools',
        'user-guide/features/mcp',
        'user-guide/features/cron',
        'user-guide/features/skins',
        'user-guide/features/voice-mode',
        'user-guide/features/computer-use',
      ],
    },
    {
      type: 'category',
      label: 'Customization',
      collapsed: true,
      items: [
        'user-guide/features/plugins',
        'user-guide/features/personality',
        'user-guide/configuring-models',
        'developer-guide/adding-providers',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      collapsed: true,
      items: [
        'reference/tools-reference',
        'reference/slash-commands',
        'reference/cli-commands',
        'reference/environment-variables',
        'reference/toolsets-reference',
        'reference/outstanding-work',
        'reference/document-generation',
        'reference/preview-control',
        'reference/faq',
      ],
    },
    {
      type: 'category',
      label: 'Programmatic',
      collapsed: true,
      items: [
        'guides/python-library',
        'user-guide/features/api-server',
        'developer-guide/programmatic-integration',
      ],
    },
    {
      type: 'category',
      label: 'Platform',
      collapsed: true,
      items: [
        'getting-started/installation',
        'getting-started/nix-setup',
        'user-guide/windows-native',
        'getting-started/termux',
        'user-guide/docker',
      ],
    },
    {
      type: 'category',
      label: 'Developer',
      collapsed: true,
      items: [
        'developer-guide/architecture',
        'developer-guide/agent-loop',
        'developer-guide/adding-tools',
        'developer-guide/adding-providers',
        'developer-guide/contributing',
      ],
    },
    // Skills catalog collapses to a single generated link (no per-skill nesting).
    'reference/skills-catalog',
  ],
};

export default sidebars;
