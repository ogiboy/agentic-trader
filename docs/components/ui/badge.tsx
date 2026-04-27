import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Slot } from 'radix-ui';

import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-none border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3!',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground data-[interactive=true]:hover:bg-primary/80',
        secondary:
          'bg-secondary text-secondary-foreground data-[interactive=true]:hover:bg-secondary/80',
        destructive:
          'bg-destructive/10 text-destructive focus-visible:ring-destructive/20 data-[interactive=true]:hover:bg-destructive/20 dark:bg-destructive/20 dark:focus-visible:ring-destructive/40',
        outline:
          'border-border text-foreground data-[interactive=true]:hover:bg-muted data-[interactive=true]:hover:text-muted-foreground',
        ghost:
          'data-[interactive=true]:hover:bg-muted data-[interactive=true]:hover:text-muted-foreground dark:data-[interactive=true]:hover:bg-muted/50',
        link: 'text-primary underline-offset-4 data-[interactive=true]:hover:underline',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

/**
 * Renders a styled badge element with variant-driven appearance.
 *
 * @param variant - Visual variant to apply (e.g., "default", "secondary", "destructive", "outline", "ghost", "link"); defaults to `"default"`.
 * @param asChild - When `true`, renders the badge as a polymorphic child element instead of a native `span` and sets `data-interactive="true"` to enable interactive hover styles.
 * @returns A JSX element (either a native `span` or a polymorphic Slot child) with the computed badge classes and data attributes applied.
 */
function Badge({
  className,
  variant = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'span'> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : 'span';

  return (
    <Comp
      data-slot="badge"
      data-interactive={asChild ? 'true' : undefined}
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
