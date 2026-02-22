import { Description, Label, SearchField } from "@heroui/react";

function readValue(valueOrEvent) {
  if (typeof valueOrEvent === "string" || typeof valueOrEvent === "number") {
    return String(valueOrEvent);
  }
  return String(valueOrEvent?.target?.value ?? "");
}

export function DashboardSearchField({
  label = "Search",
  description = "Search by ID, in-game name, account name, and related fields.",
  placeholder = "Search...",
  value = "",
  onChange,
  onKeyDown,
  name = "search",
  className,
  inputClassName = "w-full",
  isDisabled = false,
}) {
  return (
    <SearchField
      className={className}
      isDisabled={isDisabled}
      name={name}
      value={value}
      onChange={(next) => onChange?.(readValue(next))}
    >
      <Label>{label}</Label>
      <SearchField.Group>
        <SearchField.SearchIcon />
        <SearchField.Input
          className={inputClassName}
          placeholder={placeholder}
          onKeyDown={onKeyDown}
        />
        <SearchField.ClearButton />
      </SearchField.Group>
      {description ? <Description>{description}</Description> : null}
    </SearchField>
  );
}
