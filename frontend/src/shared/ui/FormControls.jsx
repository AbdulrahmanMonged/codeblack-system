import { Checkbox, Input, ListBox, Select, TextArea } from "@heroui/react";
import { forwardRef, useMemo } from "react";

function toTextValue(content, fallback = "") {
  if (typeof content === "string" || typeof content === "number") {
    return String(content);
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
      const typeName =
        typeof child.type === "string" ? child.type.toLowerCase() : "";
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

function FormCheckboxBase(
  {
    children,
    checked,
    className,
    defaultChecked,
    disabled,
    name,
    onChange,
    value = "on",
    ...rest
  },
  ref,
) {
  const isControlled = checked !== undefined;

  return (
    <Checkbox
      ref={ref}
      className={className}
      defaultSelected={defaultChecked}
      isDisabled={disabled}
      isSelected={isControlled ? Boolean(checked) : undefined}
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
      {...rest}
    >
      <Checkbox.Control>
        <Checkbox.Indicator />
      </Checkbox.Control>
      {children ? <Checkbox.Content>{children}</Checkbox.Content> : null}
    </Checkbox>
  );
}

function FormInputBase(
  { type = "text", children, checked, defaultChecked, ...rest },
  ref,
) {
  if (String(type).toLowerCase() === "checkbox") {
    return (
      <FormCheckbox
        ref={ref}
        checked={checked}
        defaultChecked={defaultChecked}
        {...rest}
      >
        {children}
      </FormCheckbox>
    );
  }

  return <Input ref={ref} type={type} {...rest} />;
}

function FormTextareaBase(props, ref) {
  return <TextArea ref={ref} {...props} />;
}

function FormSelectBase(
  {
    children,
    defaultValue,
    disabled,
    name,
    onChange,
    placeholder,
    required,
    value,
    ...rest
  },
  ref,
) {
  const options = useMemo(() => parseSelectOptions(children), [children]);
  const selectedKey =
    value === undefined || value === null ? undefined : String(value);
  const defaultSelectedKey =
    selectedKey === undefined &&
    defaultValue !== undefined &&
    defaultValue !== null
      ? String(defaultValue)
      : undefined;

  return (
    <Select
      ref={ref}
      defaultSelectedKey={defaultSelectedKey}
      isDisabled={disabled}
      isRequired={required}
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
  );
}

export const FormCheckbox = forwardRef(FormCheckboxBase);
export const FormInput = forwardRef(FormInputBase);
export const FormSelect = forwardRef(FormSelectBase);
export const FormTextarea = forwardRef(FormTextareaBase);
