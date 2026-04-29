import React, { useState, useCallback } from 'react';

interface PropertyField {
  key: string;
  label: string;
  type: 'number' | 'string' | 'color' | 'select' | 'slider' | 'checkbox' | 'vector3';
  value: unknown;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
}

export interface PropertySection {
  id: string;
  label: string;
  icon: string;
  color: string;
  fields: PropertyField[];
  collapsed?: boolean;
}

interface PropertyEditorProps {
  selectedName: string | null;
  sections: PropertySection[];
  onFieldChange: (sectionId: string, fieldKey: string, value: unknown) => void;
}

const Vector3Input: React.FC<{
  value: number[];
  onChange: (v: number[]) => void;
}> = ({ value, onChange }) => {
  const labels = ['X', 'Y', 'Z'];
  const colors = ['#ef4444', '#22c55e', '#3b82f6'];
  return (
    <div className="flex gap-1 flex-1">
      {labels.map((label, i) => (
        <div key={label} className="flex-1 flex items-center gap-1">
          <span className="text-[9px] font-bold" style={{ color: colors[i] }}>{label}</span>
          <input
            type="number"
            value={value[i] ?? 0}
            step={0.1}
            onChange={(e) => {
              const next = [...value];
              next[i] = parseFloat(e.target.value) || 0;
              onChange(next);
            }}
            className="sl-property-input flex-1 text-center !px-1"
          />
        </div>
      ))}
    </div>
  );
};

const PropertyEditor: React.FC<PropertyEditorProps> = ({
  selectedName,
  sections,
  onFieldChange,
}) => {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());

  const toggleSection = useCallback((id: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  if (!selectedName) {
    return (
      <div className="sl-panel h-full">
        <div className="sl-panel-header">
          <i className="fa-solid fa-sliders text-[10px] text-orange-500" />
          <span className="sl-panel-header-title">Inspector</span>
        </div>
        <div className="flex-1 flex items-center justify-center text-[11px] text-[#444]">
          Select an entity to inspect
        </div>
      </div>
    );
  }

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-sliders text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Inspector</span>
      </div>
      <div className="px-3 py-2 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={selectedName}
            className="sl-property-input flex-1 font-semibold"
            readOnly
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sections.map((section) => {
          const isCollapsed = collapsedSections.has(section.id);
          return (
            <div key={section.id} className="sl-property-section">
              <div
                className="sl-property-section-header"
                onClick={() => toggleSection(section.id)}
              >
                <i className={`fa-solid fa-chevron-${isCollapsed ? 'right' : 'down'} text-[8px] text-[#555]`} />
                <i className={`fa-solid ${section.icon} text-[10px]`} style={{ color: section.color }} />
                <span>{section.label}</span>
              </div>
              {!isCollapsed && section.fields.map((field) => (
                <div key={field.key} className="sl-property-row">
                  <span className="sl-property-label">{field.label}</span>
                  {field.type === 'number' && (
                    <input
                      type="number"
                      value={field.value as number}
                      step={field.step ?? 1}
                      min={field.min}
                      max={field.max}
                      onChange={(e) => onFieldChange(section.id, field.key, parseFloat(e.target.value) || 0)}
                      className="sl-property-input flex-1"
                    />
                  )}
                  {field.type === 'string' && (
                    <input
                      type="text"
                      value={field.value as string}
                      onChange={(e) => onFieldChange(section.id, field.key, e.target.value)}
                      className="sl-property-input flex-1"
                    />
                  )}
                  {field.type === 'color' && (
                    <div className="flex items-center gap-2 flex-1">
                      <input
                        type="color"
                        value={field.value as string}
                        onChange={(e) => onFieldChange(section.id, field.key, e.target.value)}
                        className="w-6 h-6 rounded cursor-pointer border border-[#2a2a2a]"
                      />
                      <input
                        type="text"
                        value={field.value as string}
                        onChange={(e) => onFieldChange(section.id, field.key, e.target.value)}
                        className="sl-property-input flex-1"
                      />
                    </div>
                  )}
                  {field.type === 'select' && (
                    <select
                      value={field.value as string}
                      onChange={(e) => onFieldChange(section.id, field.key, e.target.value)}
                      className="sl-property-input flex-1"
                    >
                      {field.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  )}
                  {field.type === 'slider' && (
                    <div className="flex items-center gap-2 flex-1">
                      <input
                        type="range"
                        value={field.value as number}
                        min={field.min ?? 0}
                        max={field.max ?? 100}
                        step={field.step ?? 1}
                        onChange={(e) => onFieldChange(section.id, field.key, parseFloat(e.target.value))}
                        className="flex-1 accent-orange-500"
                      />
                      <span className="text-[10px] text-[#666] w-8 text-right">{field.value as number}</span>
                    </div>
                  )}
                  {field.type === 'checkbox' && (
                    <label className="flex items-center gap-2 flex-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={field.value as boolean}
                        onChange={(e) => onFieldChange(section.id, field.key, e.target.checked)}
                        className="accent-orange-500"
                      />
                      <span className="text-[10px] text-[#666]">{field.value ? 'On' : 'Off'}</span>
                    </label>
                  )}
                  {field.type === 'vector3' && (
                    <Vector3Input
                      value={field.value as number[]}
                      onChange={(v) => onFieldChange(section.id, field.key, v)}
                    />
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PropertyEditor;
