import {
  Checkbox,
  Description,
  FieldError,
  Input,
  Label,
  ListBox,
  Select,
  TextArea,
} from "@heroui/react";
import { forwardRef, useId, useMemo } from "react";

function toTextValue(content, fallback = "") {
  if (typeof content === "string" || typeof content === "number") {
    return String(content);
  }
  return fallback;
}

function humanizeLabel(rawValue) {
  if (!rawValue) return "Field";
  return String(rawValue)
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function resolveLabelContent({ label, name, placeholder, fallback = "Field" }) {
  if (label !== undefined && label !== null && label !== "") {
    return label;
  }
  if (name) {
    return humanizeLabel(name);
  }
  if (typeof placeholder === "string" && placeholder.trim()) {
    return humanizeLabel(placeholder.replace(/[.]+$/, ""));
  }
  return fallback;
}

function parseSelectOptions(children) {
  return (Array.isArray(children) ? children : [children])
    .filter(Boolean)
    .flatMap((child) => {
      if (!child || typeof child !== "object" || !child.props) {
        return [];
      }
      const typeName = typeof child.type === "string" ? child.type.toLowerCase() : "";
      if (typeName !== "option") {
        return [];
      }
      const rawValue = child.props.value;
      const value =
        rawValue === undefined || rawValue === null
          ? toTextValue(child.props.children, "")
          : String(rawValue);
      const label = child.props.children;
      const textValue = toTextValue(label, value);
      return [
        {
          key: value,
          value,
          label,
          textValue,
          disabled: Boolean(child.props.disabled),
        },
      ];
    });
}

function makeSyntheticCheckboxEvent({ checked, name, value }) {
  return {
    target: {
      checked,
      name,
      type: "checkbox",
      value: value ?? "on",
    },
    currentTarget: {
      checked,
      name,
      type: "checkbox",
      value: value ?? "on",
    },
  };
}

function submitClosestForm(event) {
  const currentTarget = event?.currentTarget;
  const form =
    currentTarget?.form ||
    (typeof currentTarget?.closest === "function" ? currentTarget.closest("form") : null);

  if (form && typeof form.requestSubmit === "function") {
    event.preventDefault();
    form.requestSubmit();
  }
}

function handleInputEnterKey(event, onEnter) {
  if (event.defaultPrevented) return;
  if (event.key !== "Enter") return;
  if (event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;

  const tagName = String(event.target?.tagName || "").toLowerCase();
  if (tagName === "textarea") {
    return;
  }

  if (onEnter) {
    event.preventDefault();
    onEnter(event);
    return;
  }

  submitClosestForm(event);
}

function normalizeErrorMessage(errorMessage) {
  if (errorMessage === null || errorMessage === undefined || errorMessage === "") {
    return "";
  }
  if (typeof errorMessage === "string") {
    return errorMessage;
  }
  if (typeof errorMessage === "number") {
    return String(errorMessage);
  }
  try {
    return JSON.stringify(errorMessage);
  } catch {
    return String(errorMessage);
  }
}

function FormCheckboxBase(
  {
    children,
    checked,
    className,
    defaultChecked,
    disabled,
    description,
    errorMessage,
    isInvalid,
    isRequired,
    label,
    labelClassName,
    name,
    onChange,
    onKeyDown,
    value = "on",
    ...rest
  },
  ref,
) {
  const checkboxLabel =
    children !== undefined && children !== null && children !== ""
      ? children
      : resolveLabelContent({ label, name, fallback: "Toggle" });

  const renderedError = normalizeErrorMessage(errorMessage);

  return (
    <div className="space-y-1.5">
      <Checkbox
        ref={ref}
        className={className}
        defaultSelected={defaultChecked}
        isDisabled={disabled}
        isInvalid={isInvalid}
        isRequired={isRequired}
        isSelected={checked !== undefined ? Boolean(checked) : undefined}
        name={name}
        value={value}
        onChange={(nextChecked) =>
          onChange?.(
            makeSyntheticCheckboxEvent({
              checked: Boolean(nextChecked),
              name,
              value,
            }),
          )
        }
        onKeyDown={(event) => {
          onKeyDown?.(event);
          if (!event.defaultPrevented) {
            handleInputEnterKey(event);
          }
        }}
        {...rest}
      >
        <Checkbox.Control>
          <Checkbox.Indicator />
        </Checkbox.Control>
        <Checkbox.Content>
          <Label className={labelClassName}>{checkboxLabel}</Label>
        </Checkbox.Content>
      </Checkbox>
      {description ? <Description>{description}</Description> : null}
      {renderedError ? <FieldError>{renderedError}</FieldError> : null}
    </div>
  );
}

function FormInputBase(
  {
    type = "text",
    checked,
    defaultChecked,
    description,
    errorMessage,
    fieldClassName,
    id,
    isInvalid,
    isRequired,
    label,
    labelClassName,
    name,
    onEnter,
    onKeyDown,
    placeholder,
    ...rest
  },
  ref,
) {
  if (String(type).toLowerCase() === "checkbox") {
    return (
      <FormCheckbox
        ref={ref}
        checked={checked}
        defaultChecked={defaultChecked}
        description={description}
        errorMessage={errorMessage}
        id={id}
        isInvalid={isInvalid}
        isRequired={isRequired}
        label={label}
        labelClassName={labelClassName}
        name={name}
        onEnter={onEnter}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        {...rest}
      />
    );
  }

  const autoId = useId().replace(/[:]/g, "");
  const inputId = id || `${name || "field"}-${autoId}`;
  const labelContent = resolveLabelContent({ label, name, placeholder, fallback: "Input" });
  const renderedError = normalizeErrorMessage(errorMessage);

  return (
    <div className={fieldClassName || "space-y-1.5"}>
      <Label className={labelClassName} htmlFor={inputId} isInvalid={isInvalid} isRequired={isRequired}>
        {labelContent}
      </Label>
      <Input
        ref={ref}
        id={inputId}
        isInvalid={isInvalid || Boolean(renderedError)}
        isRequired={isRequired}
        name={name}
        placeholder={placeholder}
        type={type}
        onKeyDown={(event) => {
          onKeyDown?.(event);
          if (!event.defaultPrevented) {
            handleInputEnterKey(event, onEnter);
          }
        }}
        {...rest}
      />
      {description ? <Description>{description}</Description> : null}
      {renderedError ? <FieldError>{renderedError}</FieldError> : null}
    </div>
  );
}

function FormTextareaBase(
  {
    description,
    errorMessage,
    fieldClassName,
    id,
    isInvalid,
    isRequired,
    label,
    labelClassName,
    name,
    onEnter,
    onKeyDown,
    placeholder,
    ...rest
  },
  ref,
) {
  const autoId = useId().replace(/[:]/g, "");
  const inputId = id || `${name || "textarea"}-${autoId}`;
  const labelContent = resolveLabelContent({ label, name, placeholder, fallback: "Textarea" });
  const renderedError = normalizeErrorMessage(errorMessage);

  return (
    <div className={fieldClassName || "space-y-1.5"}>
      <Label className={labelClassName} htmlFor={inputId} isInvalid={isInvalid} isRequired={isRequired}>
        {labelContent}
      </Label>
      <TextArea
        ref={ref}
        id={inputId}
        isInvalid={isInvalid || Boolean(renderedError)}
        isRequired={isRequired}
        name={name}
        placeholder={placeholder}
        onKeyDown={(event) => {
          onKeyDown?.(event);
          if (event.defaultPrevented) {
            return;
          }
          if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.altKey &&
            (event.ctrlKey || event.metaKey)
          ) {
            if (onEnter) {
              event.preventDefault();
              onEnter(event);
            } else {
              submitClosestForm(event);
            }
          }
        }}
        {...rest}
      />
      {description ? <Description>{description}</Description> : null}
      {renderedError ? <FieldError>{renderedError}</FieldError> : null}
    </div>
  );
}

function FormSelectBase(
  {
    children,
    defaultValue,
    description,
    disabled,
    errorMessage,
    fieldClassName,
    isInvalid,
    isRequired,
    label,
    labelClassName,
    name,
    onChange,
    placeholder,
    value,
    ...rest
  },
  ref,
) {
  const options = useMemo(() => parseSelectOptions(children), [children]);
  const selectedKey = value === undefined || value === null ? undefined : String(value);
  const defaultSelectedKey =
    selectedKey === undefined && defaultValue !== undefined && defaultValue !== null
      ? String(defaultValue)
      : undefined;

  const labelContent = resolveLabelContent({ label, name, placeholder, fallback: "Select" });
  const renderedError = normalizeErrorMessage(errorMessage);

  return (
    <div className={fieldClassName || "space-y-1.5"}>
      <Select
        ref={ref}
        defaultSelectedKey={defaultSelectedKey}
        isDisabled={disabled}
        isInvalid={isInvalid || Boolean(renderedError)}
        isRequired={isRequired}
        name={name}
        placeholder={placeholder}
        selectedKey={selectedKey}
        onSelectionChange={(key) => {
          const nextValue = key === null || key === undefined ? "" : String(key);
          onChange?.({
            target: {
              name,
              value: nextValue,
            },
            currentTarget: {
              name,
              value: nextValue,
            },
          });
        }}
        {...rest}
      >
        <Label className={labelClassName} isInvalid={isInvalid} isRequired={isRequired}>
          {labelContent}
        </Label>
        <Select.Trigger>
          <Select.Value />
          <Select.Indicator />
        </Select.Trigger>
        <Select.Popover>
          <ListBox>
            {options.map((option) => (
              <ListBox.Item
                key={option.key}
                id={option.key}
                isDisabled={option.disabled}
                textValue={option.textValue}
              >
                {option.label}
                <ListBox.ItemIndicator />
              </ListBox.Item>
            ))}
          </ListBox>
        </Select.Popover>
      </Select>
      {description ? <Description>{description}</Description> : null}
      {renderedError ? <FieldError>{renderedError}</FieldError> : null}
    </div>
  );
}

export const FormCheckbox = forwardRef(FormCheckboxBase);
export const FormInput = forwardRef(FormInputBase);
export const FormSelect = forwardRef(FormSelectBase);
export const FormTextarea = forwardRef(FormTextareaBase);
