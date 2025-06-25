import type { ComponentContext, ResourceData } from '@ixon-cdk/types';
import type { ServiceLogbookCategory } from './types';

export function mapAppConfigToServiceLogbookCategoryMapFactory(context: ComponentContext) {
  return function mapAppConfigToServiceLogbookCategoryMap(
    appConfig: ResourceData.AppConfig<{ categories?: ServiceLogbookCategory[] }> | null,
  ): Map<number, ServiceLogbookCategory> {
    const categoryMap = new Map<number, ServiceLogbookCategory>();

    if (appConfig?.values) {
      const categories = appConfig.values.categories;
      if (Array.isArray(categories)) {
        for (const category of categories) {
          const id = category.id;
          const color = category.color;
          const translate = category.translate;
          const name = context.sanitizeHtml(
            translate ? context.translate(category.name, { source: 'custom' }) : category.name,
          );
          if (typeof id === 'number' && typeof name === 'string') {
            categoryMap.set(id, { id, name, color });
          }
        }
      }
    }

    return categoryMap;
  };
}

export function getCategoryStyle(category: ServiceLogbookCategory | null): string {
  if (category?.name) {
    if (category?.color) {
      return `color: ${category.color}; background-color: color-mix(in srgb, ${category.color} 18%, transparent);`;
    }

    return 'border: 1px solid var(--card-border-color)';
  }

  return '';
}
