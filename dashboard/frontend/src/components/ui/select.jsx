import React, { createContext, useContext, useState, forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

const SelectContext = createContext();

export const Select = ({ value, onValueChange, children, ...props }) => {
  const [internalValue, setInternalValue] = useState(value);
  const [isOpen, setIsOpen] = useState(false);
  
  const currentValue = value !== undefined ? value : internalValue;
  const handleValueChange = onValueChange || setInternalValue;

  return (
    <SelectContext.Provider value={{ 
      value: currentValue, 
      onValueChange: handleValueChange,
      isOpen,
      setIsOpen
    }}>
      <div className="relative" {...props}>
        {children}
      </div>
    </SelectContext.Provider>
  );
};

export const SelectTrigger = forwardRef(({ className, children, ...props }, ref) => {
  const context = useContext(SelectContext);
  
  if (!context) {
    throw new Error('SelectTrigger must be used within Select');
  }

  return (
    <button
      type="button"
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      onClick={() => context.setIsOpen(!context.isOpen)}
      ref={ref}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 opacity-50" />
    </button>
  );
});

SelectTrigger.displayName = 'SelectTrigger';

export const SelectValue = ({ placeholder, className, ...props }) => {
  const context = useContext(SelectContext);
  
  if (!context) {
    throw new Error('SelectValue must be used within Select');
  }

  return (
    <span className={cn('block truncate', className)} {...props}>
      {context.value || placeholder}
    </span>
  );
};

export const SelectContent = ({ className, children, ...props }) => {
  const context = useContext(SelectContext);
  
  if (!context) {
    throw new Error('SelectContent must be used within Select');
  }

  if (!context.isOpen) {
    return null;
  }

  return (
    <div
      className={cn(
        'absolute top-full z-50 mt-1 w-full rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95',
        className
      )}
      {...props}
    >
      <div className="p-1">
        {children}
      </div>
    </div>
  );
};

export const SelectItem = ({ value, className, children, ...props }) => {
  const context = useContext(SelectContext);
  
  if (!context) {
    throw new Error('SelectItem must be used within Select');
  }

  const isSelected = context.value === value;

  return (
    <div
      className={cn(
        'relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
        isSelected && 'bg-accent text-accent-foreground',
        className
      )}
      onClick={() => {
        context.onValueChange(value);
        context.setIsOpen(false);
      }}
      {...props}
    >
      {isSelected && (
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-current" />
        </span>
      )}
      {children}
    </div>
  );
};
