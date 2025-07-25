import React, { createContext, useContext, useState } from 'react';
import { cn } from '../../lib/utils';

const TabsContext = createContext();

export const Tabs = ({ value, onValueChange, children, className, ...props }) => {
  const [internalValue, setInternalValue] = useState(value);
  
  const currentValue = value !== undefined ? value : internalValue;
  const handleValueChange = onValueChange || setInternalValue;

  return (
    <TabsContext.Provider value={{ value: currentValue, onValueChange: handleValueChange }}>
      <div className={cn('w-full', className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
};

export const TabsList = ({ children, className, ...props }) => {
  return (
    <div
      className={cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const TabsTrigger = ({ value, children, className, ...props }) => {
  const context = useContext(TabsContext);
  
  if (!context) {
    throw new Error('TabsTrigger must be used within Tabs');
  }

  const isActive = context.value === value;

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
        isActive
          ? 'bg-background text-foreground shadow-sm'
          : 'hover:bg-background/50 hover:text-foreground',
        className
      )}
      onClick={() => context.onValueChange(value)}
      {...props}
    >
      {children}
    </button>
  );
};

export const TabsContent = ({ value, children, className, ...props }) => {
  const context = useContext(TabsContext);
  
  if (!context) {
    throw new Error('TabsContent must be used within Tabs');
  }

  if (context.value !== value) {
    return null;
  }

  return (
    <div
      className={cn(
        'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
