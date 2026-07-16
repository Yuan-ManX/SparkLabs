import React from 'react';

type ModuleCategory = 'agent' | 'engine' | 'creative' | 'system';

interface ModuleShellProps {
  title: string;
  subtitle?: string;
  icon?: string;
  category?: ModuleCategory;
  actions?: React.ReactNode;
  children: React.ReactNode;
  bodyClassName?: string;
  noPadding?: boolean;
}

const categoryIcons: Record<ModuleCategory, string> = {
  agent: 'fa-brain',
  engine: 'fa-microchip',
  creative: 'fa-wand-magic-sparkles',
  system: 'fa-gear',
};

const ModuleShell: React.FC<ModuleShellProps> = ({
  title,
  subtitle,
  icon,
  category = 'agent',
  actions,
  children,
  bodyClassName = '',
  noPadding = false,
}) => {
  const iconName = icon || categoryIcons[category];

  return (
    <div className="sl-module">
      <div className="sl-module-header">
        <div className={`sl-module-header-icon ${category}`}>
          <i className={`fa-solid ${iconName}`} />
        </div>
        <div className="flex flex-col">
          <div className="sl-module-header-title">{title}</div>
          {subtitle && <div className="sl-module-header-subtitle">{subtitle}</div>}
        </div>
        {actions && <div className="sl-module-header-actions">{actions}</div>}
      </div>
      <div className={`sl-module-body ${noPadding ? '!p-0' : ''} ${bodyClassName}`}>
        {children}
      </div>
    </div>
  );
};

export default ModuleShell;
