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
        <Button slot="trigger" variant="secondary" className={cn("w-full justify-between", triggerClassName)}>
          {title}
          <Disclosure.Indicator />
        </Button>
      </Disclosure.Heading>
      <Disclosure.Content>
        <Disclosure.Body
          className={cn("mt-3 rounded-xl border border-white/10 bg-white/5 p-3", bodyClassName)}
        >
          {children}
        </Disclosure.Body>
      </Disclosure.Content>
    </Disclosure>
  );
}
