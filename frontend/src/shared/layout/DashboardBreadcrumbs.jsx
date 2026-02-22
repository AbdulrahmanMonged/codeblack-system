import { useMemo } from "react";
import { matchPath, useLocation } from "react-router-dom";
import { Breadcrumbs } from "@heroui/react";
import { APP_NAV_SECTIONS } from "../../app/router/navigation.js";

const STATIC_ROUTE_LABELS = new Map(
  APP_NAV_SECTIONS.flatMap((section) => section.items.map((item) => [item.to, item.label])),
);

STATIC_ROUTE_LABELS.set("/verify-account", "Verify Account");

const DYNAMIC_ROUTE_BUILDERS = [
  {
    pattern: "/applications/:publicId",
    build: ({ publicId }) => [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Applications", to: "/applications" },
      { label: `Application ${publicId}` },
    ],
  },
  {
    pattern: "/orders/:publicId",
    build: ({ publicId }) => [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Orders", to: "/orders" },
      { label: `Order ${publicId}` },
    ],
  },
  {
    pattern: "/activities/:publicId",
    build: ({ publicId }) => [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Activities", to: "/activities" },
      { label: `Activity ${publicId}` },
    ],
  },
  {
    pattern: "/voting/application/:applicationId",
    build: ({ applicationId }) => [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Applications", to: "/applications" },
      { label: `Voting ${applicationId}` },
    ],
  },
  {
    pattern: "/voting/:contextType/:contextId",
    build: ({ contextType, contextId }) => [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Voting" },
      { label: `${formatToken(contextType)} ${contextId}` },
    ],
  },
];

function normalizePath(pathname) {
  const normalized = pathname.replace(/\/+$/, "");
  return normalized.length ? normalized : "/";
}

function formatToken(value = "") {
  return value
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function buildBreadcrumbItems(pathname) {
  const normalizedPath = normalizePath(pathname);

  if (normalizedPath === "/verify-account") {
    return [{ label: "Verify Account" }];
  }

  for (const definition of DYNAMIC_ROUTE_BUILDERS) {
    const match = matchPath({ path: definition.pattern, end: true }, normalizedPath);
    if (match) {
      return definition.build(match.params);
    }
  }

  if (normalizedPath === "/dashboard") {
    return [{ label: "Dashboard" }];
  }

  const staticLabel = STATIC_ROUTE_LABELS.get(normalizedPath);
  if (staticLabel) {
    return [
      { label: "Dashboard", to: "/dashboard" },
      { label: staticLabel },
    ];
  }

  const segments = normalizedPath.split("/").filter(Boolean);
  if (!segments.length) {
    return [{ label: "Dashboard" }];
  }

  const breadcrumbs = [{ label: "Dashboard", to: "/dashboard" }];
  let currentPath = "";

  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    if (currentPath === "/dashboard") {
      return;
    }

    const isLast = index === segments.length - 1;
    const label = STATIC_ROUTE_LABELS.get(currentPath) ?? formatToken(segment);
    const to = !isLast && STATIC_ROUTE_LABELS.has(currentPath) ? currentPath : undefined;

    breadcrumbs.push({ label, to });
  });

  return breadcrumbs;
}

export function DashboardBreadcrumbs() {
  const location = useLocation();
  const breadcrumbs = useMemo(
    () => buildBreadcrumbItems(location.pathname),
    [location.pathname],
  );

  return (
    <Breadcrumbs
      aria-label="Dashboard breadcrumbs"
      className="overflow-x-auto rounded-xl border border-border/40 bg-background/60 px-3 py-2 backdrop-blur"
    >
      {breadcrumbs.map((item, index) => (
        <Breadcrumbs.Item key={`${item.label}-${index}`} href={item.to}>
          {item.label}
        </Breadcrumbs.Item>
      ))}
    </Breadcrumbs>
  );
}
