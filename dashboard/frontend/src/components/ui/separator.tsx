import React, { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export const Separator = forwardRef(({ className, orientation = 'horizontal', decorative = true, ...props }, ref) => {
  return (
    <div
      ref={ref}
      role={decorative ? 'none' : 'separator'}
      aria-orientation={orientation}
      className={cn(
        'shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]',
        className
      )}
      {...props}
    />
  );
});

Separator.displayName = 'Separator';
