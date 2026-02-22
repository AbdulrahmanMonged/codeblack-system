import { Button, Disclosure, cn } from "@heroui/react";

export function FormSectionDisclosure({
  title,
  children,
  defaultExpanded = false,
  triggerClassName,
  bodyClassName,
}) {
  return (
    <Disclosure defaultExpanded={defaultExpanded}>
      <Disclosure.Heading>
        <Button
          className={cn(
            "w-full justify-between border border-white/15 bg-black/35 text-white/90 hover:bg-white/10",
            triggerClassName,
          )}
          slot="trigger"
          variant="secondary"
        >
          {title}
          <Disclosure.Indicator />
        </Button>
      </Disclosure.Heading>
      <Disclosure.Content>
        <Disclosure.Body className={cn("mt-2 p-0", bodyClassName)}>{children}</Disclosure.Body>
      </Disclosure.Content>
    </Disclosure>
  );
}
